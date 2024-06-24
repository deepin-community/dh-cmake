CMake Example
=============

This example project demonstrates how to use dh-cmake's CMake functionality. It
can be built out of the box with dpkg-buildpackage.

Look in the `debian/rules` file. Notice the `--with cmake` parameter. This
enables the `cmake` Debhelper sequence, which runs the `dh_cmake_install`
command. This command checks the `debian/` directory for `*.cmake-components`
files.

Now look at the `debian/*.cmake-components` files, and compare them with the
`CMakeLists.txt` file. `CMakeLists.txt` installs the header and library
symlink in the `Development` component, and the shared library itself in the
`Libraries` component. By listing `Libraries` in
`debian/libcmakeexample.cmake-components`, the shared library gets installed in
`libcmakeexample`. Likewise, listing `Development` in
`debian/libcmakeexample-dev.cmake-components` causes `libcmakeexample-dev` to
get the library symlink and header file.
