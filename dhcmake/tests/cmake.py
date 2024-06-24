# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import os.path

from dhcmake import common, cmake
from . import KWTestCaseBase, DebianSourcePackageTestCaseBase


class DHCMakeTestCase(DebianSourcePackageTestCaseBase):
    DHClass = cmake.DHCMake

    libraries_files = set(KWTestCaseBase.replace_arch_in_paths({
        "usr",
        "usr/lib",
        "usr/lib/{arch}",
        "usr/lib/{arch}/libdh-cmake-test.so.1",
        "usr/lib/{arch}/libdh-cmake-test.so.1.0",
        "usr/lib/{arch}/libdh-cmake-test-lib1.so.1",
        "usr/lib/{arch}/libdh-cmake-test-lib1.so.1.0",
        "usr/lib/{arch}/libdh-cmake-test-lib2.so.1",
        "usr/lib/{arch}/libdh-cmake-test-lib2.so.1.0",
    }))

    shlibs_files = {
        "DEBIAN",
        "DEBIAN/shlibs",
    }

    headers_files = set(KWTestCaseBase.replace_arch_in_paths({
        "usr",
        "usr/include",
        "usr/include/dh-cmake-test.h",
        "usr/include/dh-cmake-test-lib1.h",
        "usr/include/dh-cmake-test-lib2.h",
    }))

    namelinks_files = set(KWTestCaseBase.replace_arch_in_paths({
        "usr",
        "usr/lib",
        "usr/lib/{arch}",
        "usr/lib/{arch}/libdh-cmake-test.so",
        "usr/lib/{arch}/libdh-cmake-test-lib1.so",
        "usr/lib/{arch}/libdh-cmake-test-lib2.so",
    }))

    libdh_cmake_test_files = {
        "usr",
        "usr/share",
        "usr/share/doc",
        "usr/share/doc/libdh-cmake-test",
        "usr/share/doc/libdh-cmake-test/changelog.Debian.gz",
    }

    libdh_cmake_test_dev_files = {
        "usr",
        "usr/share",
        "usr/share/doc",
        "usr/share/doc/libdh-cmake-test-dev",
        "usr/share/doc/libdh-cmake-test-dev/changelog.Debian.gz",
    }

    def setup_do_cmake_install(self):
        self.build_dir = self.make_directory_in_tmp("build")

        self.run_cmd(
            [
                "cmake", "-G", "Unix Makefiles", "-DCMAKE_INSTALL_PREFIX=/usr",
                self.src_dir,
            ], cwd=self.build_dir)

        self.run_cmd(["make"], cwd=self.build_dir)

    def test_cmake_install_all(self):
        self.setup_do_cmake_install()
        self.dh.tool_name = "dh_test_cmake_install_all"
        self.dh.parse_args([])
        self.dh.options.sourcedir = "debian/tmp"

        self.dh.do_cmake_install(self.build_dir,
                                 "libdh-cmake-test")

        self.assertFileTreeEqual(self.libraries_files | self.headers_files
                                 | self.namelinks_files, "debian/libdh-cmake-test")

    def test_cmake_install_subdirectory(self):
        self.setup_do_cmake_install()
        self.dh.tool_name = "dh_test_cmake_install_subdirectory"
        self.dh.parse_args([])
        self.dh.options.sourcedir = "debian/tmp"

        self.dh.do_cmake_install(
            self.build_dir,
            "libdh-cmake-test", subdir="lib1")

        self.assertFileTreeEqual(set(self.replace_arch_in_paths({
            "usr",
            "usr/lib",
            "usr/lib/{arch}",
            "usr/lib/{arch}/libdh-cmake-test-lib1.so",
            "usr/lib/{arch}/libdh-cmake-test-lib1.so.1",
            "usr/lib/{arch}/libdh-cmake-test-lib1.so.1.0",
            "usr/include",
            "usr/include/dh-cmake-test-lib1.h",
        })), "debian/libdh-cmake-test")

    def test_cmake_install_one_component(self):
        self.setup_do_cmake_install()
        self.dh.tool_name = "dh_test_cmake_install_one_component"
        self.dh.parse_args([])
        self.dh.options.sourcedir = "debian/tmp"

        self.dh.do_cmake_install(self.build_dir,
                                 "libdh-cmake-test-dev",
                                 component="Headers")

        self.assertFileTreeEqual(
            self.headers_files, "debian/libdh-cmake-test-dev")
        expected_contents = "\n".join(self.replace_arch_in_paths([
            "debian/tmp/usr/include/dh-cmake-test.h",
            "debian/tmp/usr/include/dh-cmake-test-lib1.h",
            "debian/tmp/usr/include/dh-cmake-test-lib2.h",
        ])) + "\n"
        self.assertFileContentsEqual(expected_contents,
                                     "debian/.debhelper/generated/libdh-cmake-test-dev/"
                                     "installed-by-dh_test_cmake_install_one_component")

    def test_get_cmake_components(self):
        self.dh.parse_args([])

        self.assertEqual([
            "Libraries",
        ], self.dh.get_cmake_components("libdh-cmake-test"))

    def test_get_cmake_components_executable(self):
        self.dh.parse_args([])

        self.assertEqual([
            "Headers",
            "Namelinks",
        ], self.dh.get_cmake_components("libdh-cmake-test-dev"))

    def test_get_cmake_components_noexist(self):
        self.dh.parse_args([])

        self.assertEqual([], self.dh.get_cmake_components(
            "libdh-cmake-test-doc"))

    def do_dh_cmake_install(self, args):
        self.dh.parse_args(
            args, make_arg_parser=self.dh.install_make_arg_parser)

        os.mkdir(self.dh.get_build_directory())

        self.run_cmd(
            [
                "cmake", "-G", "Unix Makefiles", "-DCMAKE_INSTALL_PREFIX=/usr",
                self.src_dir,
            ], cwd=self.dh.get_build_directory())

        self.run_cmd(["make"], cwd=self.dh.get_build_directory())

        self.dh.install(args)

    def test_dh_cmake_install_default(self):
        self.do_dh_cmake_install([])

        self.assertFileTreeEqual(self.libraries_files,
                                 "debian/libdh-cmake-test")

        self.assertFileTreeEqual(self.headers_files | self.namelinks_files,
                                 "debian/libdh-cmake-test-dev")

    def test_dh_cmake_install_package_component(self):
        self.do_dh_cmake_install(["--package", "libdh-cmake-test",
                                  "--component", "Namelinks", "--component",
                                  "Libraries"])

        self.assertFileTreeEqual(self.libraries_files | self.namelinks_files,
                                 "debian/libdh-cmake-test")

    def test_dh_cmake_install_package_component_error(self):
        with self.assertRaisesRegex(
                common.PackageError,
                "Can only specify one package when specifying components"):
            self.do_dh_cmake_install(["--package", "libdh-cmake-test",
                                      "--package", "libdh-cmake-test-dev",
                                      "--component", "Namelinks",
                                      "--component", "Libraries"])

    def test_dh_cmake_install_tmpdir(self):
        self.do_dh_cmake_install(["--tmpdir=debian/tmp"])

        self.assertFileTreeEqual(self.libraries_files | self.headers_files
                                 | self.namelinks_files,
                                 "debian/tmp")

    def test_run_debian_rules(self):
        self.run_debian_rules("build", "cmake")
        self.run_debian_rules("install", "cmake")

        self.assertFileTreeEqual(self.libraries_files | self.shlibs_files
                                 | self.libdh_cmake_test_files,
                                 "debian/libdh-cmake-test")

        self.assertFileTreeEqual(self.headers_files | self.namelinks_files
                                 | self.libdh_cmake_test_dev_files,
                                 "debian/libdh-cmake-test-dev")
