# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import autopep8
import pyflakes.api
import os.path
from unittest import TestCase


class SourceCheckTestCase(TestCase):
    def foreach_py(self, func):
        test_dir = os.path.dirname(__file__)
        root_dir = os.path.dirname(os.path.dirname(test_dir))

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filter(lambda f: f.endswith(".py"), filenames):
                filename_abs = os.path.join(dirpath, filename)
                filename_rel = os.path.relpath(filename_abs, root_dir)
                with open(filename_abs) as f:
                    contents = f.read()
                func(filename_abs, filename_rel, contents)

    def test_autopep8(self):
        self.foreach_py(lambda a, r, c: self.assertEqual(autopep8.fix_code(c), c,
                                                         msg="File %s is incorrectly formatted" % r))

    def test_pyflakes(self):
        self.foreach_py(lambda a, r, c: self.assertEqual(
            0, pyflakes.api.check(c, r), msg="File %s failed pyflakes check" % r))
