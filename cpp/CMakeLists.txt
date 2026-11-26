cmake_minimum_required(VERSION 3.20)
project(fxcore VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Tipo de build" FORCE)
endif()

option(FXCORE_BUILD_PYTHON "Compila o modulo Python (pybind11)" ON)
option(FXCORE_BUILD_TESTS "Compila os testes (Catch2)" ON)
option(FXCORE_BUILD_BENCH "Compila o benchmark em C++" ON)

include(FetchContent)
find_package(Threads REQUIRED)

# ---- biblioteca ---------------------------------------------------------------
add_library(fxcore STATIC src/fxcore.cpp)
target_include_directories(fxcore PUBLIC include)
target_link_libraries(fxcore PUBLIC Threads::Threads)
set_target_properties(fxcore PROPERTIES POSITION_INDEPENDENT_CODE ON)
if(MSVC)
  target_compile_options(fxcore PRIVATE /W4)
else()
  target_compile_options(fxcore PRIVATE -Wall -Wextra -Wpedantic)
  # Vetoriza log/exp/sin/cos (libmvec). Desligue com -DFXCORE_FAST_MATH=OFF.
  option(FXCORE_FAST_MATH "Usa -ffast-math no nucleo" ON)
  if(FXCORE_FAST_MATH)
    target_compile_options(fxcore PRIVATE -ffast-math)
  endif()
endif()

# ---- modulo Python ------------------------------------------------------------
if(FXCORE_BUILD_PYTHON)
  find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
  execute_process(
    COMMAND ${Python_EXECUTABLE} -m pybind11 --cmakedir
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET)
  if(PYBIND11_CMAKE_DIR)
    list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
  endif()
  find_package(pybind11 CONFIG QUIET)
  if(NOT pybind11_FOUND)
    message(STATUS "pybind11 nao encontrado: baixando via FetchContent")
    FetchContent_Declare(pybind11
      GIT_REPOSITORY https://github.com/pybind/pybind11.git
      GIT_TAG v2.13.6)
    FetchContent_MakeAvailable(pybind11)
  endif()

  pybind11_add_module(_fxcore bindings/pybind.cpp)
  target_link_libraries(_fxcore PRIVATE fxcore)
  # O .so/.pyd vai direto para o pacote Python.
  set(FXCORE_PY_OUT "${CMAKE_CURRENT_SOURCE_DIR}/../src/fxpricer")
  set_target_properties(_fxcore PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${FXCORE_PY_OUT}"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${FXCORE_PY_OUT}"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${FXCORE_PY_OUT}"
    RUNTIME_OUTPUT_DIRECTORY "${FXCORE_PY_OUT}"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${FXCORE_PY_OUT}"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${FXCORE_PY_OUT}")
endif()

# ---- testes -------------------------------------------------------------------
if(FXCORE_BUILD_TESTS)
  enable_testing()
  FetchContent_Declare(Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.7.1)
  FetchContent_MakeAvailable(Catch2)
  add_executable(fxcore_tests tests/test_fxcore.cpp)
  target_link_libraries(fxcore_tests PRIVATE fxcore Catch2::Catch2WithMain)
  list(APPEND CMAKE_MODULE_PATH ${catch2_SOURCE_DIR}/extras)
  include(Catch)
  catch_discover_tests(fxcore_tests)
endif()

# ---- benchmark ----------------------------------------------------------------
if(FXCORE_BUILD_BENCH)
  add_executable(bench_mc benchmarks/bench_mc.cpp)
  target_link_libraries(bench_mc PRIVATE fxcore)
endif()
