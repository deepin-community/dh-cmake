# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

use warnings;
use strict;
use Debian::Debhelper::Dh_Lib;

insert_after("dh_auto_install", "dh_cmake_install");

1;
