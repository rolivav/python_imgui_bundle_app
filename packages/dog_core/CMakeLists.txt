cmake_minimum_required(VERSION 3.15...3.30)
project(dog_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python 3.10 COMPONENTS Interpreter Development.Module REQUIRED)

# nanobind is the binding layer (a leaner, faster alternative to pybind11). It
# ships its CMake configuration next to the Python package, so ask the package
# where that is and import it from there.
execute_process(
  COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
  OUTPUT_STRIP_TRAILING_WHITESPACE
  OUTPUT_VARIABLE nanobind_ROOT
)
find_package(nanobind CONFIG REQUIRED)

# nlohmann/json parses the dog.ceo response. Header-only: use a system copy when
# available, otherwise fetch the release during the build.
find_package(nlohmann_json CONFIG QUIET)
if(NOT nlohmann_json_FOUND)
  include(FetchContent)
  FetchContent_Declare(
    nlohmann_json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
  )
  FetchContent_MakeAvailable(nlohmann_json)
endif()

# The HTTP client shells out to the `curl` command line tool, so no HTTP library
# is linked at all. curl ships with Windows 10+ and with macOS; on Linux it is a
# single package (usually already installed).
nanobind_add_module(_dog_core cpp/dog_core.cpp cpp/http_curl.cpp)
target_link_libraries(_dog_core PRIVATE nlohmann_json::nlohmann_json)

install(TARGETS _dog_core DESTINATION dog_core)
