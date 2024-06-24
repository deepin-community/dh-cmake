cmake_minimum_required(VERSION 3.5)
project(libcpackexample C)

include(GNUInstallDirs)
include(CPackComponent)

add_library(cpackexample SHARED example.c)
set_target_properties(cpackexample PROPERTIES
  PUBLIC_HEADER "example.h"
  VERSION 1.0
  SOVERSION 1
)
install(TARGETS cpackexample
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Libraries
    NAMELINK_SKIP
  PUBLIC_HEADER
    DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
    COMPONENT Headers
)
install(TARGETS cpackexample
  LIBRARY
    DESTINATION "${CMAKE_INSTALL_LIBDIR}"
    COMPONENT Namelinks
    NAMELINK_ONLY
)

cpack_add_component(Libraries)
cpack_add_component(Namelinks GROUP Development DEPENDS Libraries)
cpack_add_component(Headers GROUP Development DEPENDS Libraries)

cpack_add_component_group(Development)

include(CPack)
