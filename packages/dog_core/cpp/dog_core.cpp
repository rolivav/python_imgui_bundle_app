// Native image-procurement core for the Dog panel.
//
// This is the "core" of the dog panel: the two HTTP requests to dog.ceo (the
// API call returning the URL of a random picture, then the download of that
// picture) and the JSON parsing all happen here, in C++. The Python side only
// decodes the returned bytes into pixels (Pillow) and uploads them to the GPU.
//
// The GIL is released while the network I/O is in flight, so the caller may run
// this from a worker thread without stalling the GUI.

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>  // nanobind requires the STL headers explicitly

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <string>

#include "http.hpp"

namespace nb = nanobind;
using json = nlohmann::json;

namespace {

constexpr char kApiUrl[] = "https://dog.ceo/api/breeds/image/random";

std::string title_case(const std::string& text) {
    std::string result = text;
    bool at_word_start = true;
    for (char& character : result) {
        const auto uc = static_cast<unsigned char>(character);
        if (std::isspace(uc)) {
            at_word_start = true;
            continue;
        }
        character = at_word_start ? static_cast<char>(std::toupper(uc))
                                  : static_cast<char>(std::tolower(uc));
        at_word_start = false;
    }
    return result;
}

// Human readable breed derived from a dog.ceo picture URL: the path holds a
// single "breed-sub-breed" (or just "breed") segment after "/breeds/".
std::string breed_from_image_url(const std::string& url) {
    const std::string marker = "/breeds/";
    const std::size_t marker_pos = url.find(marker);
    if (marker_pos == std::string::npos) {
        return "Dog";
    }

    const std::size_t segment_begin = marker_pos + marker.size();
    std::size_t segment_end = url.find('/', segment_begin);
    if (segment_end == std::string::npos) {
        segment_end = url.size();
    }
    const std::string segment = url.substr(segment_begin, segment_end - segment_begin);
    if (segment.empty()) {
        return "Dog";
    }

    const std::size_t dash = segment.find('-');
    std::string name = dash == std::string::npos
                           ? segment
                           : segment.substr(dash + 1) + " " + segment.substr(0, dash);
    std::replace(name.begin(), name.end(), '-', ' ');
    return title_case(name);
}

}  // namespace

// Returns (image_bytes, breed, image_url).
nb::tuple fetch_random_dog() {
    std::string image_bytes;
    std::string breed;
    std::string image_url;

    {
        nb::gil_scoped_release release;  // the network I/O never touches Python

        json payload;
        try {
            payload = json::parse(dog_core::http_get(kApiUrl));
        } catch (const json::exception& error) {
            throw std::runtime_error(std::string("could not parse the dog.ceo response: ") +
                                     error.what());
        }

        if (!payload.contains("status") || payload["status"] != "success" ||
            !payload.contains("message") || !payload["message"].is_string()) {
            throw std::runtime_error("dog.ceo returned an unexpected response");
        }

        image_url = payload["message"].get<std::string>();
        image_bytes = dog_core::http_get(image_url);
        breed = breed_from_image_url(image_url);
    }

    return nb::make_tuple(nb::bytes(image_bytes.data(), image_bytes.size()), breed, image_url);
}

NB_MODULE(_dog_core, module) {
    module.doc() = "Native image procurement for the Dog panel (HTTP + JSON in C++).";
    module.def("fetch_random_dog", &fetch_random_dog,
               "Fetch a random dog picture.\n\n"
               "Returns a tuple ``(image_bytes, breed, image_url)``: the encoded\n"
               "picture (to be decoded by the caller), its breed, and its URL.");
}
