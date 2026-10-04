//! Native image procurement for the Bird panel.
//!
//! The HTTP requests (the Ornithophile API call that picks a bird, then the
//! download of its picture) and the JSON parsing all happen here, in Rust. The
//! Python side only decodes the returned bytes into pixels (Pillow) and uploads
//! them to the GPU.
//!
//! As in `dog_core`, the HTTP client shells out to the `curl` command line tool,
//! so no HTTP or TLS library is linked in and the build stays quick. The GIL is
//! released while the network I/O is in flight, so the caller may run this from a
//! worker thread without stalling the GUI.

use std::collections::HashMap;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex, OnceLock};

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use serde::Deserialize;

/// The Ornithophile API (https://github.com/tustoz/ornithophile). It needs no API
/// key, but has no "random" endpoint either: the species of one letter of the
/// alphabet are fetched, and a bird is picked from them.
const API_ROOT: &str = "https://ornithophile.vercel.app/api/birds";
const TIMEOUT_SECONDS: u32 = 30;
/// The API hands out 250 px Wikimedia thumbnails. The width is part of the URL,
/// so a bigger one is just a matter of rewriting it (see [`download_picture`]).
const THUMBNAIL_WIDTH: u32 = 1000;

#[derive(Clone, Deserialize)]
struct Bird {
    #[serde(default)]
    common_name: String,
    #[serde(default)]
    scientific_name: String,
    #[serde(default)]
    male_image: Option<String>,
    #[serde(default)]
    female_image: Option<String>,
    #[serde(default)]
    other_images: Vec<OtherImage>,
}

#[derive(Clone, Deserialize)]
struct OtherImage {
    #[serde(default)]
    source: String,
}

/// The species list of every letter fetched so far. One list weighs about a
/// megabyte (the whole catalogue is 21 MB) and the panel asks for a new bird
/// every time its button is pressed, so keeping them is worth it.
static BIRDS_BY_LETTER: OnceLock<Mutex<HashMap<u8, Arc<Vec<Bird>>>>> = OnceLock::new();

/// `GET` the URL and return the body.
fn http_get(url: &str) -> Result<Vec<u8>, String> {
    if !url.starts_with("https://") {
        return Err(format!("refusing to fetch {url}"));
    }

    let timeout = TIMEOUT_SECONDS.to_string();
    let output = Command::new("curl")
        .args([
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time",
            &timeout,
            "--user-agent",
            "cat-gifs-imgui-bundle-app/1.0 (educational ImGui demo)",
        ])
        .arg(url)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|error| format!("could not run curl (is it on PATH?): {error}"))?;

    if !output.status.success() {
        let message = String::from_utf8_lossy(&output.stderr).trim().to_owned();
        return Err(format!("could not fetch {url}: {message}"));
    }
    Ok(output.stdout)
}

/// `GET` again when the server asks to slow down.
///
/// Wikimedia rate limits bursts of thumbnail requests (HTTP 429) and a moment
/// later the same request usually goes through, so it is retried twice with a
/// growing pause.
fn http_get_retrying(url: &str) -> Result<Vec<u8>, String> {
    const PAUSES_MS: [u64; 2] = [2000, 4000];

    let mut last_error = match http_get(url) {
        Ok(body) => return Ok(body),
        Err(error) => error,
    };
    for pause in PAUSES_MS {
        if !last_error.contains("429") {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(pause));
        last_error = match http_get(url) {
            Ok(body) => return Ok(body),
            Err(error) => format!("{last_error} ({error})"),
        };
    }
    Err(last_error)
}

/// The species whose names start with `letter`, from the cache or the API.
fn birds_starting_with(letter: u8) -> Result<Arc<Vec<Bird>>, String> {
    let cache = BIRDS_BY_LETTER.get_or_init(|| Mutex::new(HashMap::new()));
    if let Some(birds) = cache
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .get(&letter)
    {
        return Ok(Arc::clone(birds));
    }

    let url = format!("{API_ROOT}/alpha/{}", letter as char);
    let birds: Vec<Bird> = serde_json::from_slice(&http_get_retrying(&url)?)
        .map_err(|error| format!("could not parse the Ornithophile response: {error}"))?;
    let birds = Arc::new(birds);
    cache
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .insert(letter, Arc::clone(&birds));
    Ok(birds)
}

/// A picture of a bird, at a resolution worth showing.
///
/// The species photos come first, then the other images.
fn picture_url(bird: &Bird) -> Option<String> {
    let candidate = bird
        .male_image
        .iter()
        .chain(bird.female_image.iter())
        .chain(bird.other_images.iter().map(|image| &image.source))
        .map(String::as_str)
        .find(|url| is_usable_image(url))?;

    // The API returns protocol relative URLs ("//upload.wikimedia.org/...").
    let url = if candidate.starts_with("//") {
        format!("https:{candidate}")
    } else {
        candidate.to_owned()
    };
    Some(url)
}

/// Whether an image URL from the API is worth fetching.
///
/// Photographs are mixed with diagrams and documents - the IUCN status maps
/// (`.svg.png`) and scans (`.tif`, tens of megabytes) among them - so only
/// Wikimedia thumbnails of web images are taken.
fn is_usable_image(url: &str) -> bool {
    let url = url.to_ascii_lowercase();
    if url.is_empty() || url.contains(".svg") {
        return false;
    }
    url.contains("px-") // a thumbnail, i.e. "<width>px-<file>"
        || url.ends_with(".jpg")
        || url.ends_with(".jpeg")
        || url.ends_with(".png")
        || url.ends_with(".gif")
        || url.ends_with(".webp")
}

/// The same thumbnail URL at another width: `.../<file>/250px-<file>` becomes
/// `.../<file>/<width>px-<file>`. `None` when the URL carries no width.
fn with_thumbnail_width(url: &str, width: u32) -> Option<String> {
    let (head, last) = url.rsplit_once('/')?;
    let (size, file) = last.split_once("px-")?;
    if size.is_empty() || !size.chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    Some(format!("{head}/{width}px-{file}"))
}

/// Download a picture of a bird.
///
/// The 250 px thumbnail the API points at is asked for at [`THUMBNAIL_WIDTH`]
/// instead, and Wikimedia answers 400 when that is wider than the original file
/// (common for the smaller species photos); the 250 px URL is then used as it
/// is. Anything larger is never fetched: some of the source files are scans of
/// tens of megabytes.
fn download_picture(url: &str) -> Result<Vec<u8>, String> {
    if let Some(large) = with_thumbnail_width(url, THUMBNAIL_WIDTH) {
        match http_get_retrying(&large) {
            Ok(bytes) => return Ok(bytes),
            // Being rate limited says nothing about the width, and it has already
            // been retried, so that is reported rather than asked for again.
            Err(error) if error.contains("429") => return Err(error),
            // 400: the original is narrower than THUMBNAIL_WIDTH, so the 250 px
            // URL is the widest version Wikimedia has.
            Err(_) => {}
        }
    }
    http_get_retrying(url)
}

/// Returns `(image_bytes, common_name, scientific_name, image_url)`.
///
/// Runs without the GIL; the caller must re-acquire it before touching Python.
fn fetch_random_bird_blocking() -> Result<(Vec<u8>, String, String, String), String> {
    let birds = birds_starting_with(fastrand::u8(b'a'..=b'z'))?;

    let with_picture: Vec<(&Bird, String)> = birds
        .iter()
        .filter_map(|bird| picture_url(bird).map(|url| (bird, url)))
        .collect();
    if with_picture.is_empty() {
        return Err("the Ornithophile API returned no bird with a picture".to_owned());
    }

    let (bird, image_url) = &with_picture[fastrand::usize(..with_picture.len())];
    let image_bytes = download_picture(image_url)?;
    Ok((
        image_bytes,
        bird.common_name.clone(),
        bird.scientific_name.clone(),
        image_url.clone(),
    ))
}

/// Fetch a random bird picture, returning `(image_bytes, name, sci_name, url)`.
///
/// Blocking; the GIL is released for the duration of the network I/O.
#[pyfunction]
fn fetch_random_bird(py: Python<'_>) -> PyResult<(Vec<u8>, String, String, String)> {
    py.allow_threads(fetch_random_bird_blocking)
        .map_err(PyRuntimeError::new_err)
}

#[pymodule]
fn _bird_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(fetch_random_bird, module)?)?;
    module.add(
        "__doc__",
        "Native image procurement for the Bird panel (HTTP + JSON in Rust).",
    )?;
    Ok(())
}
