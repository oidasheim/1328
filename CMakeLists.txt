cmake_minimum_required(VERSION 3.20)
project(synapse_granular LANGUAGES CXX)

add_library(synapse_granular STATIC native/granular_synth.cpp)
target_include_directories(synapse_granular PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/native)
target_compile_features(synapse_granular PUBLIC cxx_std_20)

if(MSVC)
  target_compile_options(synapse_granular PRIVATE /W4 /permissive-)
else()
  target_compile_options(synapse_granular PRIVATE -Wall -Wextra -Wpedantic)
endif()

include(CTest)
if(BUILD_TESTING)
  add_executable(test_granular tests/native/test_granular.cpp)
  target_link_libraries(test_granular PRIVATE synapse_granular)
  add_test(NAME granular_kernel COMMAND test_granular)
endif()
