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

add_executable(EventDrivenSim
    src/main.cpp
    src/utils/neighbours.cpp
)


target_include_directories(EventDrivenSim PRIVATE src/utils/include)
target_link_libraries(EventDrivenSim PRIVATE argparse)
