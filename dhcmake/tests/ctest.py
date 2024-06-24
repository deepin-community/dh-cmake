# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import http.server
import re
import subprocess
import threading
import urllib.parse
import xml.etree.ElementTree
import os

from dhcmake import ctest
from . import DebianSourcePackageTestCaseBase, KWTestCaseBase


class PushEnvironmentVariable:
    def __init__(self, name, value):
        self.name = name
        try:
            self.old_value = os.environ[name]
        except KeyError:
            self.old_value = None

        os.environ[name] = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_value is None:
            del os.environ[self.name]
        else:
            os.environ[self.name] = self.old_value


class PushEnvironmentVariableTestCase(KWTestCaseBase):
    varname = "DH_CMAKE_TEST_VARIABLE_DO_NOT_SET"

    def test_create_new(self):
        try:
            del os.environ[self.varname]
        except KeyError:
            pass

        with PushEnvironmentVariable(self.varname, "value"):
            self.assertEqual("value", os.environ[self.varname])

        self.assertNotIn(self.varname, os.environ)

    def test_change(self):
        os.environ[self.varname] = "old"

        with PushEnvironmentVariable(self.varname, "new"):
            self.assertEqual("new", os.environ[self.varname])

        self.assertEqual("old", os.environ[self.varname])


class MockCDashServerHandler(http.server.BaseHTTPRequestHandler):
    def do_PUT(self):
        match = re.search(r"^/submit\.php\?(.*)$", self.path)
        if not match:
            self.send_error(404)
            return
        query_string_params = urllib.parse.parse_qs(match.group(1))

        if query_string_params["project"] != ["dh-cmake-test"]:
            self.send_error(404)
            return

        self.send_response(100)
        self.end_headers()
        self.flush_headers()

        input_file = self.rfile.read(int(self.headers.get("content-length")))
        self.server.submitted_files.add(input_file)

        self.send_response(200)
        self.end_headers()
        self.flush_headers()

    def log_message(self, format, *args):
        pass


class MockCDashServer(http.server.HTTPServer):
    def __init__(self, server_address):
        super().__init__(server_address, MockCDashServerHandler)

        self.submitted_files = set()


class DHCTestTestCase(DebianSourcePackageTestCaseBase):
    DHClass = ctest.DHCTest

    def setUp(self):
        super().setUp()

        try:
            del os.environ["DEB_CTEST_OPTIONS"]
        except KeyError:
            pass  # No variable, no problem

        self.cdash_server = MockCDashServer(("localhost", 47806))
        self.cdash_server_thread = \
            threading.Thread(target=self.cdash_server.serve_forever)
        self.cdash_server_thread.daemon = True
        self.cdash_server_thread.start()

    def tearDown(self):
        self.cdash_server.shutdown()
        self.cdash_server_thread.join()
        self.cdash_server.server_close()

        super().tearDown()

    def assertFilesSubmittedEqual(self, steps):
        contents_set = set()
        for step in steps:
            date = self.get_testing_tag_date()
            with open(os.path.join("debian/.ctest/Testing", date,
                                   step + ".xml"), "rb") as f:
                contents = f.read()
            contents_set.add(contents)

        self.assertEqual(contents_set, self.cdash_server.submitted_files)

    def get_testing_tag_date(self):
        with open("debian/.ctest/Testing/TAG", "r") as f:
            return next(f).rstrip()

    def test_get_deb_ctest_option(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "opt1 opt2=val  opt3=\"spaced value\" opt4=another\\ \\ space"):
            self.assertEqual(True, ctest.get_deb_ctest_option("opt1"))
            self.assertEqual("val", ctest.get_deb_ctest_option("opt2"))
            self.assertEqual(
                "spaced value", ctest.get_deb_ctest_option("opt3"))
            self.assertEqual("another  space",
                             ctest.get_deb_ctest_option("opt4"))

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "opt1=\"a"):
            with self.assertRaisesRegex(ValueError, "Unclosed quote"):
                ctest.get_deb_ctest_option("opt1")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "opt1=a\\"):
            with self.assertRaisesRegex(ValueError, "Unclosed backslash"):
                ctest.get_deb_ctest_option("opt1")

    def test_clean(self):
        os.makedirs("debian/.ctest/Testing")
        with open("debian/.ctest/Testing/TAG", "w") as f:
            f.write("")
        self.dh.clean([])
        self.assertFileNotExists("debian/.ctest")

    def test_clean_dir(self):
        os.makedirs("debian/ctest/Testing")
        with open("debian/ctest/Testing/TAG", "w") as f:
            f.write("")
        self.dh.clean(["--ctest-testing-dir", "debian/ctest"])
        self.assertFileNotExists("debian/.ctest")

    def test_start_none(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")
        self.dh.start([])
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

    def test_start_experimental(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental track=\"Experimental Track\""):
            self.dh.start([])
            with open("debian/.ctest/Testing/TAG", "r") as f:
                self.assertRegex(next(f), "^[0-9]{8}-[0-9]{4}$")
                self.assertEqual("Experimental Track", next(f).rstrip())
                try:  # Extra line here as of CMake 3.12
                    self.assertEqual("Experimental", next(f).rstrip())
                except StopIteration:
                    pass
                with self.assertRaises(StopIteration):
                    next(f)

    def test_start_experimental_dir(self):
        self.assertFileNotExists("dummydir/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start(["--ctest-testing-dir=dummydir"])
            with open("dummydir/Testing/TAG", "r") as f:
                self.assertRegex(next(f), "^[0-9]{8}-[0-9]{4}$")
                self.assertEqual("Experimental", next(f).rstrip())
                try:  # Extra line here as of CMake 3.12
                    self.assertEqual("Experimental", next(f).rstrip())
                except StopIteration:
                    pass
                with self.assertRaises(StopIteration):
                    next(f)

    def test_start_nightly(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS", "model=Nightly"):
            self.dh.start([])
            with open("debian/.ctest/Testing/TAG", "r") as f:
                self.assertRegex(next(f), "^[0-9]{8}-[0-9]{4}$")
                self.assertEqual("Nightly", next(f).rstrip())
                try:  # Extra line here as of CMake 3.12
                    self.assertEqual("Nightly", next(f).rstrip())
                except StopIteration:
                    pass
                with self.assertRaises(StopIteration):
                    next(f)

    def test_no_update_experimental(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing", date,
                                                  "Update.xml"))

    def test_update_experimental(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update"):
            self.run_cmd(["git", "init", "."])
            self.run_cmd(["git", "add", "."])
            self.run_cmd(["git", "commit", "-m", "Initial commit"], env={
                "GIT_AUTHOR_NAME": "Kitware Robot",
                "GIT_AUTHOR_EMAIL": "kwrobot@kitware.com",
                "GIT_AUTHOR_DATE": "2020.01.01T00:00:00",
                "GIT_COMMITTER_NAME": "Kitware Robot",
                "GIT_COMMITTER_EMAIL": "kwrobot@kitware.com",
                "GIT_COMMITTER_DATE": "2020.01.01T00:00:00",
            })
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "--quiet", "--format=%H"]).rstrip().decode("utf-8"),
                revision.text)

    def test_update_experimental_modified(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update"):
            self.run_cmd(["git", "init", "."])
            self.run_cmd(["git", "add", "."])
            self.run_cmd(["git", "commit", "-m", "Initial commit"], env={
                "GIT_AUTHOR_NAME": "Kitware Robot",
                "GIT_AUTHOR_EMAIL": "kwrobot@kitware.com",
                "GIT_AUTHOR_DATE": "2020.01.01T00:00:00",
                "GIT_COMMITTER_NAME": "Kitware Robot",
                "GIT_COMMITTER_EMAIL": "kwrobot@kitware.com",
                "GIT_COMMITTER_DATE": "2020.01.01T00:00:00",
            })
            os.unlink("CMakeLists.txt")
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "--quiet", "--format=%H"]).rstrip().decode("utf-8"),
                revision.text)

    def test_update_experimental_submit(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update submit"):
            self.run_cmd(["git", "init", "."])
            self.run_cmd(["git", "add", "."])
            self.run_cmd(["git", "commit", "-m", "Initial commit"], env={
                "GIT_AUTHOR_NAME": "Kitware Robot",
                "GIT_AUTHOR_EMAIL": "kwrobot@kitware.com",
                "GIT_AUTHOR_DATE": "2020.01.01T00:00:00",
                "GIT_COMMITTER_NAME": "Kitware Robot",
                "GIT_COMMITTER_EMAIL": "kwrobot@kitware.com",
                "GIT_COMMITTER_DATE": "2020.01.01T00:00:00",
            })
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "--quiet", "--format=%H"]).rstrip().decode("utf-8"),
                revision.text)

            self.assertFilesSubmittedEqual({"Update"})

    def test_update_experimental_no_submit(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update submit"):
            self.run_cmd(["git", "init", "."])
            self.run_cmd(["git", "add", "."])
            self.run_cmd(["git", "commit", "-m", "Initial commit"], env={
                "GIT_AUTHOR_NAME": "Kitware Robot",
                "GIT_AUTHOR_EMAIL": "kwrobot@kitware.com",
                "GIT_AUTHOR_DATE": "2020.01.01T00:00:00",
                "GIT_COMMITTER_NAME": "Kitware Robot",
                "GIT_COMMITTER_EMAIL": "kwrobot@kitware.com",
                "GIT_COMMITTER_DATE": "2020.01.01T00:00:00",
            })
            self.dh.start([])
            self.dh.update(["--no-submit"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "--quiet", "--format=%H"]).rstrip().decode("utf-8"),
                revision.text)

            self.assertFilesSubmittedEqual({})

    def test_update_experimental_revision(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update revision=1.0"):
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual("1.0", revision.text)

    def test_update_experimental_revision_git(self):
        self.assertFileNotExists("debian/.ctest/Testing/TAG")

        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental update revision=1.0"):
            self.run_cmd(["git", "init", "."])
            self.run_cmd(["git", "add", "."])
            self.run_cmd(["git", "commit", "-m", "Initial commit"], env={
                "GIT_AUTHOR_NAME": "Kitware Robot",
                "GIT_AUTHOR_EMAIL": "kwrobot@kitware.com",
                "GIT_AUTHOR_DATE": "2020.01.01T00:00:00",
                "GIT_COMMITTER_NAME": "Kitware Robot",
                "GIT_COMMITTER_EMAIL": "kwrobot@kitware.com",
                "GIT_COMMITTER_DATE": "2020.01.01T00:00:00",
            })
            self.dh.start([])
            self.dh.update([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Update.xml"))

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Update.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            update_type = self.get_single_element(tree.findall(
                "UpdateType"))
            self.assertEqual("GIT", update_type.text)
            revision = self.get_single_element(tree.findall(
                "Revision"))
            self.assertEqual("1.0", revision.text)

    def test_configure_none(self):
        self.dh.start([])
        self.dh.configure([])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))
        self.assertFileExists(os.path.join(self.dh.get_build_directory(),
                                           "CMakeCache.txt"))

    def test_configure_none_bad(self):
        self.dh.start([])
        with self.assertRaises(subprocess.CalledProcessError):
            self.dh.configure(
                ["--", "-DDH_CMAKE_ENABLE_BAD_CONFIGURE:BOOL=ON"])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))
        self.assertFileExists(os.path.join(self.dh.get_build_directory(),
                                           "CMakeCache.txt"))

    def test_configure_experimental(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFileNotExists(
                os.path.join(self.dh.get_build_directory(),
                             "testflag.txt"))

            self.assertFilesSubmittedEqual({})

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Configure.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            self.assertEqual("(empty)", tree.attrib["Name"])
            self.assertEqual("(empty)", tree.attrib["BuildName"])

    def test_configure_experimental_site_build_names(self):
        with PushEnvironmentVariable(
                "DEB_CTEST_OPTIONS",
                "model=Experimental site=debtest build=debian-cmake"):
            self.dh.start(["--ctest-build-suffix=-test"])
            self.dh.configure([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Configure.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            self.assertEqual("debtest", tree.attrib["Name"])
            self.assertEqual("debian-cmake-test", tree.attrib["BuildName"])

    def test_configure_experimental_site_build_names_arg(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental site=debtest"):
            self.dh.start(["--ctest-build=debian-cmake-test"])
            self.dh.configure([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date,
                                   "Configure.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            self.assertEqual("debtest", tree.attrib["Name"])
            self.assertEqual("debian-cmake-test", tree.attrib["BuildName"])

    def test_configure_experimental_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFileNotExists(
                os.path.join(self.dh.get_build_directory(),
                             "testflag.txt"))

            self.assertFilesSubmittedEqual({"Configure"})

    def test_configure_experimental_no_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure(["-O--no-submit"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFileNotExists(
                os.path.join(self.dh.get_build_directory(),
                             "testflag.txt"))

            self.assertFilesSubmittedEqual({})

    def test_configure_experimental_args(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure(["--", "-DDH_CMAKE_TEST_FLAG:BOOL=ON"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFileExists(
                os.path.join(self.dh.get_build_directory(),
                             "testflag.txt"))

    def test_configure_experimental_bad(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            with self.assertRaises(subprocess.CalledProcessError):
                self.dh.configure([
                    "--", "-DDH_CMAKE_ENABLE_BAD_CONFIGURE:BOOL=ON"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFilesSubmittedEqual({})

    def test_configure_experimental_bad_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            with self.assertRaises(subprocess.CalledProcessError):
                self.dh.configure([
                    "--", "-DDH_CMAKE_ENABLE_BAD_CONFIGURE:BOOL=ON"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Configure.xml"))

            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Build.xml"))

            self.assertFilesSubmittedEqual({"Configure"})

    def test_build_none(self):
        self.dh.start([])
        self.dh.configure([])
        self.dh.build([])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))
        self.assertFileExists(os.path.join(self.dh.get_build_directory(),
                                           "CMakeCache.txt"))
        self.assertFileExists(os.path.join(self.dh.get_build_directory(),
                                           "libdh-cmake-test.so"))

    def test_build_none_bad(self):
        self.dh.start([])
        self.dh.configure(["--", "-DDH_CMAKE_ENABLE_BAD_BUILD:BOOL=ON"])
        with self.assertRaises(subprocess.CalledProcessError):
            self.dh.build([])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))
        self.assertFileExists(os.path.join(self.dh.get_build_directory(),
                                           "CMakeCache.txt"))

    def test_build_experimental(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Build.xml"))
            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Test.xml"))

            self.assertFilesSubmittedEqual({})

    def test_build_experimental_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Build.xml"))
            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Test.xml"))

            self.assertFilesSubmittedEqual({"Configure", "Build"})

    def test_build_experimental_no_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build(["-O--no-submit"])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Build.xml"))
            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Test.xml"))

            self.assertFilesSubmittedEqual({"Configure"})

    def test_build_experimental_bad(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_BUILD:BOOL=ON"])
            with self.assertRaises(subprocess.CalledProcessError):
                self.dh.build([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Build.xml"))
            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Test.xml"))

            self.assertFilesSubmittedEqual({})

    def test_build_experimental_bad_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_BUILD:BOOL=ON"])
            with self.assertRaises(subprocess.CalledProcessError):
                self.dh.build([])
            date = self.get_testing_tag_date()

            self.assertFileExists(os.path.join("debian/.ctest/Testing", date,
                                               "Build.xml"))
            self.assertFileNotExists(os.path.join("debian/.ctest/Testing",
                                                  date, "Test.xml"))

            self.assertFilesSubmittedEqual({"Configure", "Build"})

    def test_test_none(self):
        self.dh.start([])
        self.dh.configure([])
        self.dh.build([])
        self.dh.test([])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))

    def test_test_none_bad(self):
        self.dh.start([])
        self.dh.configure(["--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
        self.dh.build([])
        with self.assertRaises(subprocess.CalledProcessError):
            self.dh.test([])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))

    def test_test_none_bad_exclude(self):
        self.dh.start([])
        self.dh.configure(["--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
        self.dh.build([])
        self.dh.test(["--", "-E", "TestFalse"])

        self.assertFileNotExists(os.path.join("debian/.ctest/Testing/TAG"))

    def test_test_experimental(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build([])
            self.dh.test([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(1, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            self.assertFilesSubmittedEqual({})

    def test_test_experimental_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build([])
            self.dh.test([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(1, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            self.assertFilesSubmittedEqual({"Configure", "Build", "Test"})

    def test_test_experimental_no_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([])
            self.dh.build([])
            self.dh.test(["-O--no-submit"])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(1, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            self.assertFilesSubmittedEqual({"Configure", "Build"})

    def test_test_experimental_bad(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
            self.dh.build([])
            self.dh.test([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(2, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            test_false = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestFalse']"))
            self.assertEqual("failed", test_false.get("Status"))

            self.assertFilesSubmittedEqual({})

    def test_test_experimental_bad_exclude(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
            self.dh.build([])
            self.dh.test(["--", "-E", "TestFalse"])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(1, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            self.assertFilesSubmittedEqual({})

    def test_test_experimental_bad_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
            self.dh.build([])
            self.dh.test([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(2, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            test_false = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestFalse']"))
            self.assertEqual("failed", test_false.get("Status"))

            self.assertFilesSubmittedEqual({"Configure", "Build", "Test"})

    def test_test_experimental_bad_catchfailed_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental catchfailed submit"):
            self.dh.start([])
            self.dh.configure([
                "--", "-DDH_CMAKE_ENABLE_BAD_TEST:BOOL=ON"])
            self.dh.build([])
            with self.assertRaises(subprocess.CalledProcessError):
                self.dh.test([])
            date = self.get_testing_tag_date()

            with open(os.path.join("debian/.ctest/Testing", date, "Test.xml"),
                      "r") as f:
                tree = xml.etree.ElementTree.fromstring(f.read())

            tests = tree.findall("Testing/Test")
            self.assertEqual(2, len(tests))

            test_true = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestTrue']"))
            self.assertEqual("passed", test_true.get("Status"))

            test_false = self.get_single_element(tree.findall(
                "Testing/Test[Name='TestFalse']"))
            self.assertEqual("failed", test_false.get("Status"))

            self.assertFilesSubmittedEqual({"Configure", "Build", "Test"})

    def test_submit_none(self):
        self.dh.start([])
        self.dh.configure(["-O--no-submit"])
        self.dh.build(["-O--no-submit"])
        self.dh.test(["-O--no-submit"])
        self.dh.submit([])

        self.assertFilesSubmittedEqual(set())

    def test_submit_experimental_nosubmit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.dh.start([])
            self.dh.configure(["-O--no-submit"])
            self.dh.build(["-O--no-submit"])
            self.dh.test(["-O--no-submit"])
            self.dh.submit([])

            self.assertFilesSubmittedEqual(set())

    def test_submit_experimental_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure(["-O--no-submit"])
            self.dh.build(["-O--no-submit"])
            self.dh.test(["-O--no-submit"])
            self.dh.submit([])

            self.assertFilesSubmittedEqual(
                {"Configure", "Build", "Test", "Done"})

    def test_submit_experimental_submit_parts(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.dh.start([])
            self.dh.configure(["-O--no-submit"])
            self.dh.build(["-O--no-submit"])
            self.dh.test(["-O--no-submit"])
            self.dh.submit(["--parts", "Configure", "Build"])

            self.assertFilesSubmittedEqual({"Configure", "Build"})

    def test_run_debian_rules_none(self):
        self.run_debian_rules("build", "ctest")

        self.assertFileNotExists("debian/.ctest/Testing/TAG")
        self.assertFileExists("debian/build/CMakeCache.txt")
        self.assertFilesSubmittedEqual(set())

        self.run_debian_rules("clean", "ctest")
        self.assertFileNotExists("debian/.ctest")

    def test_run_debian_rules_experimental(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental"):
            self.run_debian_rules("build", "ctest")

            self.assertFileExists("debian/.ctest/Testing/TAG")
            self.assertFileExists("debian/build/CMakeCache.txt")
            self.assertFilesSubmittedEqual(set())

            self.run_debian_rules("clean", "ctest")
            self.assertFileNotExists("debian/.ctest")

    def test_run_debian_rules_experimental_submit(self):
        with PushEnvironmentVariable("DEB_CTEST_OPTIONS",
                                     "model=Experimental submit"):
            self.run_debian_rules("build", "ctest")

            self.assertFileExists("debian/.ctest/Testing/TAG")
            self.assertFileExists("debian/build/CMakeCache.txt")
            self.assertFilesSubmittedEqual(
                {"Configure", "Build", "Test", "Done"})

            self.run_debian_rules("clean", "ctest")
            self.assertFileNotExists("debian/.ctest")
