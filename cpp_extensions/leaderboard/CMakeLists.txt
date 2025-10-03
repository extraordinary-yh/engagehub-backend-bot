set(LEADERBOARD_CORE_SOURCES
    src/skip_list.cpp
    src/time_decay.cpp
    src/leaderboard.cpp)

add_library(leaderboard_core STATIC ${LEADERBOARD_CORE_SOURCES})
target_include_directories(leaderboard_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

pybind11_add_module(cpp_leaderboard src/bindings.cpp)

target_link_libraries(cpp_leaderboard
    PRIVATE
        leaderboard_core
        pybind11::module
)

target_include_directories(cpp_leaderboard
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(leaderboard_tests
    tests/test_skip_list.cpp
    tests/benchmark.cpp
)

target_link_libraries(leaderboard_tests
    PRIVATE
        leaderboard_core
        Catch2::Catch2WithMain
)

target_include_directories(leaderboard_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_test(NAME leaderboard_tests COMMAND leaderboard_tests)
