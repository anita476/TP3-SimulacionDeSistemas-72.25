cmake_minimum_required(VERSION 3.16)

project(EventDriven-TP3 LANGUAGES CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

include(FetchContent)

FetchContent_Declare(
    argparse
    GIT_REPOSITORY https://github.com/p-ranav/argparse.git
    GIT_TAG v3.2
)

FetchContent_MakeAvailable(argparse)

# -------------------------
# Core simulation library
# -------------------------

add_library(sim_core
    src/utils/neighbours.cpp
    src/utils/collision.cpp
)

target_include_directories(sim_core PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils/include
)

# -------------------------
# Main executable
# -------------------------

add_executable(EventDrivenSim
    src/main.cpp
)

target_link_libraries(EventDrivenSim PRIVATE
    sim_core
    argparse
)

# -------------------------
# Tests
# -------------------------

# Each tests/test_*.cpp is a standalone executable
file(GLOB TEST_SOURCES CONFIGURE_DEPENDS tests/test_*.cpp)
foreach(test_src ${TEST_SOURCES})
    get_filename_component(name ${test_src} NAME_WE)
    add_executable(${name} ${test_src})
    target_include_directories(${name} PRIVATE tests)
    target_link_libraries(${name} PRIVATE sim_core)
    add_test(NAME ${name} COMMAND ${name})
endforeach()