set(EVENT_PROCESSOR_CORE_SOURCES
    src/ring_buffer.cpp
    src/count_min_sketch.cpp
    src/hyperloglog.cpp
    src/thread_pool.cpp
    src/event_processor.cpp)

add_library(event_processor_core STATIC ${EVENT_PROCESSOR_CORE_SOURCES})
target_include_directories(event_processor_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

pybind11_add_module(cpp_event_processor src/bindings.cpp)

target_link_libraries(cpp_event_processor
    PRIVATE
        event_processor_core
        pybind11::module
)

target_include_directories(cpp_event_processor
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(event_processor_tests
    tests/test_ring_buffer.cpp
    tests/test_cms.cpp
    tests/benchmark.cpp
)

target_link_libraries(event_processor_tests
    PRIVATE
        event_processor_core
        Catch2::Catch2WithMain
)

target_include_directories(event_processor_tests
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_test(NAME event_processor_tests COMMAND event_processor_tests)
