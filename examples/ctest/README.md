CTest Example
=============

This example project demonstrates how to use dh-cmake's CTest functionality. It
can be built out of the box with dpkg-buildpackage. The `CMakeLists.txt` file
and `CTestConfig.cmake` file contain the project's CTest configuration.

This tutorial assumes you already know how to use CTest. If not, please refer
to the [CTest manual](https://cmake.org/cmake/help/latest/manual/ctest.1.html).

Look in the `debian/rules` file. Notice the `--with ctest` parameter. This
enables the `ctest` Debhelper sequence, which runs the `dh_ctest_start`,
`dh_ctest_configure`, `dh_ctest_build`, and `dh_ctest_test` commands.
`dh_ctest_start` starts a CTest dashboard test, while the rest of the commands
replace and wrap their `dh_auto_*` counterparts, capturing their output for the
dashboard test.

To activate dashboard mode, run `dpkg-buildpackage` with the following
environment variable (warning for the privacy-minded: this will submit the
results of the configure, build, and test steps to Kitware's public CDash
server, along with some information about your machine specs):

```shell
DEB_CTEST_OPTIONS="model=Experimental site=<hostname> build=debian-dpkg submit" dpkg-buildpackage
```

When running this command, replace `<hostname>` with your computer's hostname.

Once the package has been built, go to the
[Kitware public dashboard](https://open.cdash.org/index.php?project=PublicDashboard)
and see the results of your tests in the "Experimental" section.

Note that dashboard mode and the submission feature are completely optional.
If you don't set `DEB_CTEST_OPTIONS` and just run `dpkg-buildpackage`, it will
simply run the `dh_auto_*` commands the same way it normally would, without
capturing their output or sending anything to a server.
