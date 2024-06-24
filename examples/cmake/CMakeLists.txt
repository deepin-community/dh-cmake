cmake_minimum_required(VERSION 3.5)
project(libcmakeexample C)

include(GNUInstallDirs)

add_library(cmakeexample SHARED example.c)
set_target_properties(cmakeexample PROPERTIES
  PUBLIC_HEADER "example.h"
  VERSION 1.0
  SOVERSION 1
)
install(TARGETS cmakeexample
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Libraries
    NAMELINK_SKIP
  PUBLIC_HEADER
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
    COMPONENT Development
)
install(TARGETS cmakeexample
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Development
    NAMELINK_ONLY
)
