# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import os.path

from dhcmake import deb822
from . import KWTestCaseBase


class Deb822TestCase(KWTestCaseBase):
    def test_control(self):
        test_dir = os.path.dirname(os.path.abspath(__file__))
        test_data_dir = os.path.join(test_dir, "data")

        with open(os.path.join(test_data_dir, "debian_pkg/debian/control"),
                  "r") as f:
            source, packages = deb822.read_control(f)

        self.assertEqual("dh-cmake-test", source["source"])

        self.assertEqual(6, len(packages))

        package = packages[0]
        self.assertEqual("libdh-cmake-test", package["package"])
        self.assertEqual(["any"], package.architecture)

        package = packages[1]
        self.assertEqual("libdh-cmake-test-dev", package["package"])
        self.assertEqual(["any"], package.architecture)

        package = packages[2]
        self.assertEqual("libdh-cmake-test-doc", package["package"])
        self.assertEqual(["all"], package.architecture)

        package = packages[3]
        self.assertEqual("libdh-cmake-test-extra-32", package["package"])
        self.assertEqual(["armhf"], package.architecture)

        package = packages[4]
        self.assertEqual("libdh-cmake-test-extra-64", package["package"])
        self.assertEqual(["arm64"], package.architecture)

        package = packages[5]
        self.assertEqual("libdh-cmake-test-extra-both", package["package"])
        self.assertEqual(["armhf", "arm64"], package.architecture)
