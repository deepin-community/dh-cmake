#!/usr/bin/env python3

# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

from setuptools import setup
import debian.changelog
import os.path


def get_current_version():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    changelog_file = os.path.join(root_dir, "debian/changelog")
    with open(changelog_file) as f:
        changelog = debian.changelog.Changelog(f)
    return str(changelog.version)


def debian_version_to_python_version(version_str):
    if version_str[-1] == "~":
        return version_str[:-1] + ".dev1"
    return version_str


setup(
    name="dh-cmake",
    version=debian_version_to_python_version(get_current_version()),
    description="Debhelper program for CMake projects",
    url="https://gitlab.kitware.com/debian/dh-cmake",
    author="Kyle Edwards",
    author_email="kyle.edwards@kitware.com",
    maintainer="Kitware Debian Maintainers",
    maintainer_email="debian@kitware.com",
    classifiers=[
        "License :: OSI Approved :: BSD License",
    ],
    packages=["dhcmake"],
    test_suite="dhcmake.tests",
    install_requires=["python-debian"],
    entry_points={
        "console_scripts": [
            "dh_cmake_install=dhcmake.cmake:install",
            "dh_ctest_clean=dhcmake.ctest:clean",
            "dh_ctest_start=dhcmake.ctest:start",
            "dh_ctest_update=dhcmake.ctest:update",
            "dh_ctest_configure=dhcmake.ctest:configure",
            "dh_ctest_build=dhcmake.ctest:build",
            "dh_ctest_test=dhcmake.ctest:test",
            "dh_ctest_submit=dhcmake.ctest:submit",
            "dh_cpack_generate=dhcmake.cpack:generate",
            "dh_cpack_substvars=dhcmake.cpack:substvars",
            "dh_cpack_install=dhcmake.cpack:install",
        ],
    },
    package_data={
        "dhcmake": ["dh_ctest_driver.cmake"],
    },
    data_files=[
        ("share/perl5/Debian/Debhelper/Sequence", [
            "sequence/cmake.pm",
            "sequence/ctest.pm",
            "sequence/cpack.pm",
        ]),
        ("share/doc/dh-cmake", [
            "README.md",
        ]),
    ],
)
