# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

set(CTEST_PROJECT_NAME "dh-cmake-test")
set(CTEST_NIGHTLY_START_TIME "01:00:00 UTC")

set(CTEST_DROP_METHOD "http")
set(CTEST_DROP_SITE "localhost:47806")
set(CTEST_DROP_LOCATION "/submit.php?project=dh-cmake-test")
set(CTEST_DROP_SITE_CDASH TRUE)
