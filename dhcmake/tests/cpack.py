# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import contextlib
import os
from dhcmake import cpack, arch
from . import DebianSourcePackageTestCaseBase, KWTestCaseBase

from debian import debfile, deb822


class DHCPackTestCase(DebianSourcePackageTestCaseBase):
    DHClass = cpack.DHCPack

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

    def setUp(self):
        super().setUp()

        self.dh.parse_args([])

        os.mkdir(self.dh.get_build_directory())

        self.run_cmd(
            [
                "cmake", "-G", "Unix Makefiles", "-DCMAKE_INSTALL_PREFIX=/usr",
                self.src_dir,
            ], cwd=self.dh.get_build_directory())

        self.run_cmd(["make"], cwd=self.dh.get_build_directory())

    def test_generate(self):
        self.assertFileNotExists("debian/.cpack/cpack-metadata.json")
        self.dh.generate([])
        self.assertFileExists("debian/.cpack/cpack-metadata.json")

    def test_get_cpack_components(self):
        with open("debian/libdh-cmake-test-extra-32.cpack-components", "w") \
                as f:
            f.write("InvalidComponent\n")

        self.dh.generate([])
        self.dh.read_cpack_metadata()

        self.assertEqual(
            ["Libraries"],
            self.dh.get_cpack_components("libdh-cmake-test")
        )

        with self.assertRaises(
                ValueError,
                msg="Invalid CPack components in libdh-cmake-test-extra-32"
        ):
            self.dh.get_cpack_components("libdh-cmake-test-extra-32")

    def test_get_cpack_component_groups(self):
        with open("debian/libdh-cmake-test-extra-32.cpack-component-groups",
                  "w") as f:
            f.write("InvalidGroup\n")

        self.dh.generate([])
        self.dh.read_cpack_metadata()

        self.assertEqual(
            ["Development"],
            self.dh.get_cpack_component_groups("libdh-cmake-test-dev")
        )

        with self.assertRaises(
                ValueError,
                msg="Invalid CPack component groups "
                    "in libdh-cmake-test-extra-32"
        ):
            self.dh.get_cpack_component_groups("libdh-cmake-test-extra-32")

    def test_get_all_cpack_components_for_group(self):
        self.dh.generate([])
        self.dh.read_cpack_metadata()

        self.assertEqual({"Headers", "Namelinks"},
                         self.dh.get_all_cpack_components_for_group("Development"))

        self.assertEqual({"Libraries", "Headers", "Namelinks"},
                         self.dh.get_all_cpack_components_for_group("All"))

    def test_get_all_cpack_components(self):
        self.dh.generate([])
        self.dh.read_cpack_metadata()

        self.assertEqual({"Headers", "Namelinks"},
                         self.dh.get_all_cpack_components("libdh-cmake-test-dev"))

        self.assertEqual({"Libraries"},
                         self.dh.get_all_cpack_components("libdh-cmake-test"))

    def test_get_package_dependencies(self):
        self.dh.generate([])
        self.dh.read_cpack_metadata()

        self.assertEqual({"libdh-cmake-test"},
                         self.dh.get_package_dependencies("libdh-cmake-test-dev"))

    def test_get_package_dependencies_packages(self):
        self.dh.generate(["--package", "libdh-cmake-test-dev"])
        self.dh.read_cpack_metadata()

        self.assertEqual(set(),
                         self.dh.get_package_dependencies("libdh-cmake-test-dev"))

    def test_substvars(self):
        self.dh.generate([])
        self.dh.substvars([])

        with open("debian/libdh-cmake-test-dev.substvars", "r") as f:
            self.assertEqual("cpack:Depends=libdh-cmake-test "
                             "(= ${binary:Version})\n", f.read())

    def test_substvars_packages(self):
        self.dh.generate([])
        self.dh.substvars(["--package", "libdh-cmake-test-dev"])

        self.assertFileNotExists("debian/libdh-cmake-test-dev.substvars")

    def test_install(self):
        self.dh.generate([])
        self.dh.install([])

        self.assertFileTreeEqual(self.libraries_files,
                                 "debian/libdh-cmake-test")

        self.assertFileTreeEqual(self.headers_files | self.namelinks_files,
                                 "debian/libdh-cmake-test-dev")

    def test_run_debian_rules(self):
        self.run_debian_rules("build", "cpack")
        self.run_debian_rules("install", "cpack")

        self.assertFileTreeEqual(self.libraries_files | self.shlibs_files
                                 | self.libdh_cmake_test_files,
                                 "debian/libdh-cmake-test")

        self.assertFileTreeEqual(self.headers_files | self.namelinks_files
                                 | self.libdh_cmake_test_dev_files,
                                 "debian/libdh-cmake-test-dev")

        self.run_debian_rules("binary", "cpack")

        with contextlib.closing(debfile.DebFile(
            "../libdh-cmake-test-dev_0.1-1_%s.deb" %
                arch.dpkg_architecture()["DEB_HOST_ARCH"])) as f:
            packages = deb822.Packages(f.debcontrol())

            self.assertEqual([
                [
                    {
                        "name": "libdh-cmake-test",
                        "archqual": None,
                        "version": ("=", "0.1-1"),
                        "arch": None,
                        "restrictions": None,
                    },
                ],
            ], packages.relations["depends"])
