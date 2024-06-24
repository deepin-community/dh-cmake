# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

use warnings;
use strict;
use Debian::Debhelper::Dh_Lib;

insert_before("dh_auto_configure", "dh_ctest_configure");
remove_command("dh_auto_configure");

insert_before("dh_auto_build", "dh_ctest_build");
remove_command("dh_auto_build");

insert_before("dh_auto_test", "dh_ctest_test");
remove_command("dh_auto_test");

insert_before("dh_ctest_configure", "dh_ctest_start");
insert_after("dh_ctest_start", "dh_ctest_update");

insert_after("dh_ctest_test", "dh_ctest_submit");

insert_before("dh_clean", "dh_ctest_clean");

1;
