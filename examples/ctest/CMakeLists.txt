cmake_minimum_required(VERSION 3.5)
project(ctestexample C)

include(GNUInstallDirs)
include(CTest)

add_executable(ctestexample example.c)
install(TARGETS ctestexample
  RUNTIME
  DESTINATION "${CMAKE_INSTALL_BINDIR}"
  )

add_test(
  NAME PrintsHello
  COMMAND
    "${CMAKE_COMMAND}"
      -DCTESTEXAMPLE_COMMAND:PATH=$<TARGET_FILE:ctestexample>
      -P "${CMAKE_SOURCE_DIR}/test_hello.cmake"
  )
