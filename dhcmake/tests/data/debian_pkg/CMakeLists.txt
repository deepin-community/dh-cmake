cmake_minimum_required(VERSION 3.5)
project(dh-cmake-test C)

include(GNUInstallDirs)
include(CTest)
include(CPackComponent)

cpack_add_component(Libraries
  DISPLAY_NAME "Runtime libraries"
  DESCRIPTION "Shared library files"
  GROUP All
)

cpack_add_component(Headers
  DISPLAY_NAME "Header files"
  DESCRIPTION "#include files for the library"
  GROUP Development
  DEPENDS Libraries
)

cpack_add_component(Namelinks
  DISPLAY_NAME "Shared library symbolic links"
  DESCRIPTION "Symbolic links for the library"
  GROUP Development
  DEPENDS Libraries
)

cpack_add_component_group(All
  DISPLAY_NAME "All components"
  DESCRIPTION "Every component in the package"
)

cpack_add_component_group(Development
  DISPLAY_NAME "Development files"
  DESCRIPTION "Development files for the library"
  PARENT_GROUP All
)

macro(declare_lib LIBNAME)
  add_library(${LIBNAME} SHARED "${LIBNAME}.c")
  set_target_properties(${LIBNAME} PROPERTIES
    PUBLIC_HEADER "${LIBNAME}.h"
    VERSION 1.0
    SOVERSION 1
  )
  install(TARGETS ${LIBNAME}
    LIBRARY
      DESTINATION "${CMAKE_INSTALL_LIBDIR}"
      COMPONENT Libraries
      NAMELINK_SKIP
    PUBLIC_HEADER
      DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
      COMPONENT Headers
  )
  install(TARGETS ${LIBNAME}
    LIBRARY
      DESTINATION "${CMAKE_INSTALL_LIBDIR}"
      COMPONENT Namelinks
      NAMELINK_ONLY
  )
endmacro()

declare_lib(dh-cmake-test)
add_subdirectory(lib1)
add_subdirectory(lib2)

option(DH_CMAKE_TEST_FLAG "For testing -D definitions" OFF)
if(DH_CMAKE_TEST_FLAG)
  file(WRITE "${CMAKE_BINARY_DIR}/testflag.txt" "Test flag set\n")
endif()

add_test(TestTrue true)

option(DH_CMAKE_ENABLE_BAD_CONFIGURE "Enable bad configure" OFF)
if(DH_CMAKE_ENABLE_BAD_CONFIGURE)
  message(FATAL_ERROR "Bad configure enabled")
endif()

option(DH_CMAKE_ENABLE_BAD_BUILD "Enable bad build" OFF)
if(DH_CMAKE_ENABLE_BAD_BUILD)
  add_custom_target(badtarget ALL COMMAND false)
endif()

option(DH_CMAKE_ENABLE_BAD_TEST "Enable bad test" OFF)
if(DH_CMAKE_ENABLE_BAD_TEST)
  add_test(TestFalse false)
endif()

include(CPack)
