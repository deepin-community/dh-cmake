# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.


import subprocess


_known_archs = dict()


def debarch_is(real, alias):
    global _known_archs
    try:
        result = _known_archs[(real, alias)]
    except KeyError:
        result = subprocess.run(
            ["dpkg-architecture", "-i", alias, "-a", real, "-f"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0
        _known_archs[(real, alias)] = result
    return result


def debarch_contains(real, aliases):
    for alias in aliases:
        if debarch_is(real, alias):
            return True
    return False


_dpkg_architecture_values = None


def dpkg_architecture():
    global _dpkg_architecture_values
    if _dpkg_architecture_values is None:
        _dpkg_architecture_values = dict()
        proc = subprocess.run(["dpkg-architecture"], stdout=subprocess.PIPE)
        output = proc.stdout.decode()
        for line in output.split("\n"):
            if line:
                key, value = line.split("=", maxsplit=1)
                _dpkg_architecture_values[key] = value

    return _dpkg_architecture_values
