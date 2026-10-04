// HTTP client implementation that shells out to the `curl` command line tool.
//
// Nothing is linked: no libcurl, no WinHTTP. curl ships with Windows 10+ (in
// System32) and with macOS; on Linux it is normally installed already. The
// process is spawned on a pipe and its stdout (the response body) is read back
// in binary mode.

#include "http.hpp"

#include <array>
#include <cstdio>
#include <stdexcept>
#include <string>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#define DOG_CORE_POPEN _popen
#define DOG_CORE_PCLOSE _pclose
#else
#define DOG_CORE_POPEN popen
#define DOG_CORE_PCLOSE pclose
#endif

namespace dog_core {
namespace {

constexpr char kUserAgent[] = "cat-gifs-imgui-bundle-app/1.0";
constexpr int kTimeoutSeconds = 15;

// curl runs through a shell (cmd.exe / sh), so the URL must not be able to break
// out of the command line. The URLs we fetch come from dog.ceo and never contain
// any of these; the check keeps that a hard requirement.
bool is_safe_url(const std::string& url) {
    if (url.rfind("https://", 0) != 0 && url.rfind("http://", 0) != 0) {
        return false;
    }
    return url.find_first_of("\"'`$%\\ \t\r\n;&|<>()") == std::string::npos;
}

}  // namespace

std::string http_get(const std::string& url) {
    if (!is_safe_url(url)) {
        throw std::runtime_error("refusing to fetch an unexpected URL");
    }

    // -sS: no progress meter, but report errors.
    // -f:  exit non-zero on an HTTP error status.
    // -L:  follow redirects.
    const std::string command = "curl -sS -f -L --max-time " + std::to_string(kTimeoutSeconds) +
                                " -A \"" + kUserAgent + "\" \"" + url + "\"";

    FILE* pipe = DOG_CORE_POPEN(command.c_str(), "rb");
    if (pipe == nullptr) {
        throw std::runtime_error("could not run curl (is it installed and on PATH?)");
    }
#ifdef _WIN32
    // Without this the pipe translates newlines and corrupts the image bytes.
    _setmode(_fileno(pipe), _O_BINARY);
#endif

    std::string body;
    std::array<char, 16 * 1024> buffer{};
    for (;;) {
        const std::size_t read = std::fread(buffer.data(), 1, buffer.size(), pipe);
        body.append(buffer.data(), read);
        if (read < buffer.size()) {
            break;
        }
    }

    const int status = DOG_CORE_PCLOSE(pipe);
    if (status != 0) {
        throw std::runtime_error("curl failed (exit code " + std::to_string(status) + ")");
    }
    return body;
}

}  // namespace dog_core
