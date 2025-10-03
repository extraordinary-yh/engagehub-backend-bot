cmake_minimum_required(VERSION 3.16)
project(engagehub_cpp_extensions LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_compile_options(-O3 -march=native -Wall -Wextra -Wpedantic)

find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG QUIET)

include(FetchContent)

if(NOT pybind11_FOUND)
  message(STATUS "pybind11 not found in system, fetching via FetchContent")
  FetchContent_Declare(
    pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.11.1
  )
  FetchContent_MakeAvailable(pybind11)
endif()
if(DEFINED pybind11_SOURCE_DIR)
  set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${pybind11_SOURCE_DIR}/tools)
endif()

# Fetch Catch2 for unit tests
FetchContent_Declare(
  Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG v3.5.1
)
FetchContent_MakeAvailable(Catch2)

enable_testing()

add_subdirectory(event_processor)
add_subdirectory(leaderboard)
