CMake Example
=============

This example project demonstrates how to use dh-cmake's CPack functionality. It
can be built out of the box with dpkg-buildpackage.

Look in the `debian/rules` file. Notice the `--with cpack` parameter. This
enables the `cpack` Debhelper sequence, which runs the `dh_cpack_generate`,
`dh_cpack_substvars`, and `dh_cpack_install` commands. The generate step
generates a .json file containing the CPack metadata, the substvars step puts
this metadata into the packages' substvars, and the install step installs the
CPack components and component groups in the respective packages.

The install step is very similar to `dh_cmake_install`, but it also supports
entire CPack groups. Look at `debian/libcpackexample.cpack-components` and
`debian/libcpackexample-dev.cpack-component-groups`, and compare these with the
`CMakeLists.txt` file.

Now look at `debian/control`. Notice the use of `${cpack:Depends}` in the
`libcpackexample-dev` package. This variable makes use of CPack's own internal
dependency graph. Because the `Headers` and `Namelink` components depend on the
`Libraries` component, `libcpackexample-dev` will depend on `libcpackexample`.
