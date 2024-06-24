# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import os
from dhcmake import common, arch
from . import DebianSourcePackageTestCaseBase, VolatileNamedTemporaryFile


class DHCommonTestCase(DebianSourcePackageTestCaseBase):
    DHClass = common.DHCommon

    def setUp(self):
        super().setUp()
        self.deb_host_arch_old = arch.dpkg_architecture()["DEB_HOST_ARCH"]
        arch.dpkg_architecture()["DEB_HOST_ARCH"] = "armhf"

    def tearDown(self):
        arch.dpkg_architecture()["DEB_HOST_ARCH"] = self.deb_host_arch_old
        super().tearDown()

    def check_packages(self, expected_packages):
        self.assertEqual(expected_packages, set(self.dh.get_packages()))

    def strip_dh_cmake_compat(self):
        contents = ""
        with open("debian/control", "r") as f:
            for l in f:
                if l != "    dh-cmake-compat (= 1),\n":
                    contents += l
        with open("debian/control", "w") as f:
            f.write(contents)

    def test_do_cmd(self):
        self.dh.parse_args([])

        with VolatileNamedTemporaryFile() as f:
            self.dh.do_cmd(["rm", f.name])
            self.assertVolatileFileNotExists(f.name)

    def test_do_cmd_no_act(self):
        self.dh.parse_args(["--no-act"])

        with VolatileNamedTemporaryFile() as f:
            self.dh.do_cmd(["rm", f.name])
            self.assertFileExists(f.name)

    def test_get_packages_default(self):
        self.dh.parse_args([])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-dev",
            "libdh-cmake-test-doc",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_whitelist_short(self):
        self.dh.parse_args(["-plibdh-cmake-test-dev",
                            "-plibdh-cmake-test-doc"])

        self.check_packages({
            "libdh-cmake-test-dev",
            "libdh-cmake-test-doc",
        })

    def test_get_packages_whitelist_long(self):
        self.dh.parse_args(["--package", "libdh-cmake-test-dev",
                            "--package", "libdh-cmake-test-doc"])

        self.check_packages({
            "libdh-cmake-test-dev",
            "libdh-cmake-test-doc",
        })

    def test_get_packages_blacklist_short(self):
        self.dh.parse_args(["-Nlibdh-cmake-test-dev",
                            "-Nlibdh-cmake-test-doc"])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_blacklist_long(self):
        self.dh.parse_args(["--no-package", "libdh-cmake-test-dev",
                            "--no-package", "libdh-cmake-test-doc"])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_arch_short(self):
        self.dh.parse_args(["-a"])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-dev",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_arch_long(self):
        self.dh.parse_args(["--arch"])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-dev",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_arch_deprecated(self):
        self.dh.parse_args(["-s"])

        self.check_packages({
            "libdh-cmake-test",
            "libdh-cmake-test-dev",
            "libdh-cmake-test-extra-32",
            "libdh-cmake-test-extra-both",
        })

    def test_get_packages_indep_short(self):
        self.dh.parse_args(["-i"])

        self.check_packages({
            "libdh-cmake-test-doc",
        })

    def test_get_packages_indep_long(self):
        self.dh.parse_args(["--indep"])

        self.check_packages({
            "libdh-cmake-test-doc",
        })

    def test_get_main_package_default(self):
        self.dh.parse_args([])

        self.assertEqual("libdh-cmake-test",
                         self.dh.get_main_package())

    def test_get_main_package_specified(self):
        self.dh.parse_args(["--mainpackage=libdh-cmake-test-dev"])

        self.assertEqual("libdh-cmake-test-dev",
                         self.dh.get_main_package())

    def test_get_package_file(self):
        self.dh.parse_args([])

        self.assertEqual(
            "debian/cmake-components",
            self.dh.get_package_file(
                "libdh-cmake-test", "cmake-components"
            )
        )

        self.assertEqual(
            "debian/libdh-cmake-test-dev.cmake-components",
            self.dh.get_package_file(
                "libdh-cmake-test-dev", "cmake-components"
            )
        )

        self.assertIsNone(self.dh.get_package_file(
            "libdh-cmake-test-doc", "cmake-components"))

        self.assertEqual(
            "debian/libdh-cmake-test.specific",
            self.dh.get_package_file(
                "libdh-cmake-test", "specific"
            )
        )

        self.assertEqual(
            "debian/libdh-cmake-test.both",
            self.dh.get_package_file(
                "libdh-cmake-test", "both"
            )
        )

    def test_read_package_file(self):
        self.dh.parse_args([])

        with self.dh.read_package_file(
                "libdh-cmake-test", "cmake-components") as f:
            self.assertEqual(
                "# This file tests both comments and blank lines\n\n"
                "Libraries\n", f.read())
        with self.dh.read_package_file(
                "libdh-cmake-test-dev", "cmake-components") as f:
            self.assertEqual("Headers\nNamelinks\n", f.read())
        self.assertIsNone(self.dh.read_package_file(
            "libdh-cmake-test-doc", "cmake-components"))

    def test_build_directory_default(self):
        self.dh.parse_args([])

        self.assertEqual(
            "obj-" + arch.dpkg_architecture()["DEB_HOST_GNU_TYPE"],
            self.dh.get_build_directory())

    def test_build_directory_short(self):
        self.dh.parse_args(["-B", "debian/build"])

        self.assertEqual("debian/build",
                         self.dh.get_build_directory())

    def test_build_directory_long(self):
        self.dh.parse_args(["--builddirectory", "debian/build"])

        self.assertEqual("debian/build",
                         self.dh.get_build_directory())

    def test_tmpdir_default(self):
        self.dh.parse_args([])

        self.assertEqual("debian/libdh-cmake-test",
                         self.dh.get_tmpdir("libdh-cmake-test"))
        self.assertEqual("debian/libdh-cmake-test-dev",
                         self.dh.get_tmpdir("libdh-cmake-test-dev"))

    def test_tmpdir_short(self):
        self.dh.parse_args(["-P", "debian/tmpdir"])

        self.assertEqual("debian/tmpdir",
                         self.dh.get_tmpdir("libdh-cmake-test"))
        self.assertEqual("debian/tmpdir",
                         self.dh.get_tmpdir("libdh-cmake-test-dev"))

    def test_tmpdir_long(self):
        self.dh.parse_args(["--tmpdir=debian/tmpdir"])

        self.assertEqual("debian/tmpdir",
                         self.dh.get_tmpdir("libdh-cmake-test"))
        self.assertEqual("debian/tmpdir",
                         self.dh.get_tmpdir("libdh-cmake-test-dev"))

    def test_o_flag(self):
        self.dh.parse_args(["-O=-v"])

        self.assertTrue(self.dh.options.verbose)

    def test_compat_valid(self):
        self.assertEqual(1, self.dh.compat())

    def test_compat_low(self):
        self.strip_dh_cmake_compat()
        with open("debian/dh-cmake.compat", "w") as f:
            print(common.MIN_COMPAT - 1, file=f)

        with self.assertRaisesRegex(
            common.CompatError,
            r"Compat level %i too old \(must be %i or newer\)"
                % (common.MIN_COMPAT - 1, common.MIN_COMPAT)):
            self.dh.compat()

    def test_compat_high(self):
        self.strip_dh_cmake_compat()
        with open("debian/dh-cmake.compat", "w") as f:
            print(common.MAX_COMPAT + 1, file=f)

        with self.assertRaisesRegex(
            common.CompatError,
            r"Compat level %i too new \(must be %i or older\)"
                % (common.MAX_COMPAT + 1, common.MAX_COMPAT)):
            self.dh.compat()

    def test_compat_missing(self):
        self.strip_dh_cmake_compat()
        os.unlink("debian/dh-cmake.compat")

        with self.assertRaisesRegex(
                common.CompatError,
                "No compat level specified"):
            self.dh.compat()

    def test_compat_conflicting(self):
        with open("debian/dh-cmake.compat", "w") as f:
            print(2, file=f)

        with self.assertRaisesRegex(
                common.CompatError,
                "Conflicting compat levels: 1, 2"):
            self.dh.compat()


class DHCommonCompatTestClass(common.DHCommon):
    @common.DHEntryPoint("dh_common_test_command")
    def test_command(self, args=None):
        self.parse_args(args)
        # Do nothing


class DHCommonCompatTestCase(DebianSourcePackageTestCaseBase):
    DHClass = DHCommonCompatTestClass

    def test_compat_load(self):
        self.assertIs(None, self.dh._compat)
        self.dh.test_command([])
        self.assertEqual(1, self.dh._compat)
        self.assertEqual("dh_common_test_command", self.dh.tool_name)
