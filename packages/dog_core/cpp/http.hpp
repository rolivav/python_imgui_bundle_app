// Minimal HTTP client interface used by the dog-core extension.
//
// Implemented by invoking the `curl` command line tool (see http_curl.cpp), so
// no HTTP library is linked. Follows redirects and speaks HTTPS. curl must be
// available on PATH at runtime (it ships with Windows 10+ and with macOS).

#pragma once

#include <string>

namespace dog_core {

// GET `url` and return the response body. Throws std::runtime_error on a
// network error or a non-2xx status.
std::string http_get(const std::string& url);

}  // namespace dog_core
