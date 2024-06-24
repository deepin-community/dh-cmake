# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import re

import debian.deb822


def read_control(sequence, *args, **kwargs):
    iterator = debian.deb822.Deb822.iter_paragraphs(sequence, *args, **kwargs)
    source = ControlSource(next(iterator).dump())
    packages = [ControlPackage(p.dump()) for p in iterator]

    return source, packages


class ControlSource(debian.deb822.Deb822):
    pass


class ControlPackage(debian.deb822.Deb822):
    @property
    def architecture(self):
        return re.split("\\s+", self["architecture"])
