# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import argparse
import io
import os.path
import subprocess
import sys

from dhcmake import deb822, arch
import debian.deb822


MIN_COMPAT = 1
MAX_COMPAT = 1


class CompatError(Exception):
    pass


class PackageError(Exception):
    pass


def format_arg_for_print(arg):
    arg = arg.replace("\\", "\\\\")
    arg = arg.replace('"', '\\"')
    arg = arg.replace("'", "\\'")
    arg = arg.replace("$", "\\$")
    if " " in arg:
        return '"%s"' % arg
    else:
        return arg


def escape_substvar(value):
    value = value.replace("$", "${}")
    value = value.replace("\n", "${Newline}")

    return value


def DHEntryPoint(tool_name):
    def wrapper(func):
        def wrapped(self, *args, **kargs):
            self.tool_name = tool_name
            self.compat()
            return func(self, *args, **kargs)

        return wrapped
    return wrapper


class DHCommon:
    def __init__(self):
        self.options = argparse.Namespace()
        self.options.type = "both"
        self.stdout = sys.stdout
        self.stdout_b = sys.stdout
        self.stderr = sys.stderr
        self.stderr_b = sys.stderr
        self._compat = None

    def _parse_args(self, parser, args, known):
        if known:
            parser.parse_known_args(args=args, namespace=self.options)
        else:
            parser.parse_args(args=args, namespace=self.options)

        if self.options.options:
            options = self.options.options
            self.options.options = []
            self._parse_args(parser, options, True)

    def _set_compat(self, compat):
        if self._compat is not None and self._compat != compat:
            raise CompatError("Conflicting compat levels: %i, %i" %
                              (self._compat, compat))
        self._compat = compat

    def compat(self):
        if self._compat is None:
            with open("debian/control", "r") as f:
                source, _ = deb822.read_control(f)
            try:
                deps = source["Build-Depends"]
            except KeyError:
                deps = None
            if deps:
                deps_parsed = debian.deb822.PkgRelation.parse_relations(deps)
                for dep in deps_parsed:
                    for subdep in dep:
                        if subdep["name"] == "dh-cmake-compat" and subdep["version"]:
                            sign, version = subdep["version"]
                            if sign == "=":
                                self._set_compat(int(version))

            try:
                with open("debian/dh-cmake.compat", "r") as f:
                    self._set_compat(int(f.read()))
            except FileNotFoundError:
                pass

            if self._compat is None:
                raise CompatError("No compat level specified")

            if self._compat < MIN_COMPAT:
                raise CompatError(
                    "Compat level %i too old (must be %i or newer)" %
                    (self._compat, MIN_COMPAT))
            elif self._compat > MAX_COMPAT:
                raise CompatError(
                    "Compat level %i too new (must be %i or older)" %
                    (self._compat, MAX_COMPAT))

        return self._compat

    def parse_args(self, args=None, make_arg_parser=None):
        parser = argparse.ArgumentParser()
        if make_arg_parser:
            make_arg_parser(parser)
        else:
            self.make_arg_parser(parser)

        if args is None:
            self.parsed_args = sys.argv[1:]
        else:
            self.parsed_args = list(args)

        self._parse_args(parser, args, False)

    def make_arg_parser(self, parser):
        # Required arguments
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Verbose output")
        parser.add_argument(
            "--no-act", action="store_true",
            help="Dry run (don't actually do anything)")
        parser.add_argument(
            "-a", "-s", "--arch", action="store_const", const="arch",
            dest="type", help="Act on all architecture dependent packages")
        parser.add_argument(
            "-i", "--indep", action="store_const", const="indep",
            dest="type", help="Act on all architecture independent packages")
        parser.add_argument(
            "-p", "--package", action="append",
            help="Act on a specific package or set of packages")
        parser.add_argument(
            "-N", "--no-package", action="append",
            help="Do not act on a specific package or set of packages")
        parser.add_argument(
            "--remaining-packages", action="append",
            help="Do not act on packages which have already been acted on")
        parser.add_argument(
            "--ignore", action="append", help="Ignore a file or set of files")
        parser.add_argument(
            "-P", "--tmpdir", action="store",
            help="Use tmpdir for package build directory")
        parser.add_argument(
            "--mainpackage", action="store",
            help="Change which package is the \"main package\"")
        parser.add_argument(
            "-O", action="append",
            help="Pass additional arguments to called programs",
            dest="options")

        # More arguments
        parser.add_argument(
            "-B", "--builddirectory", action="store",
            help="Build directory for out of source building",
            default="obj-"
            + arch.dpkg_architecture()["DEB_HOST_GNU_TYPE"])

    def print_cmd(self, args, cwd=None):
        if self.options.verbose:
            args = list(args)
            if cwd:
                args = ["cd", cwd, "&&"] + args
            print_args = (format_arg_for_print(a) for a in args)
            print("\t" + " ".join(print_args), file=self.stdout)

    def do_cmd(self, args, env=None, cwd=None):
        self.print_cmd(args, cwd)
        if not self.options.no_act:
            subprocess.run(args, stdout=self.stdout, stderr=self.stderr,
                           env=env, cwd=cwd, check=True)

    def get_all_packages(self):
        with open("debian/control", "r") as f:
            source, packages = deb822.read_control(f)

        result = []

        for p in packages:
            name = p["package"]
            if p.architecture == ["all"]:
                result.append((name, p, "indep"))
            else:
                result.append((name, p, "arch"))

        return result

    def get_compatible_packages(self):
        deb_host_arch = arch.dpkg_architecture()["DEB_HOST_ARCH"]
        result = []

        for name, p, ptype in self.get_all_packages():
            if ptype == "indep" or \
                    arch.debarch_contains(deb_host_arch, p.architecture):
                result.append((name, p, ptype))

        return result

    def get_packages(self):
        result = []

        for name, p, ptype in self.get_compatible_packages():
            if self.options.package:
                if name in self.options.package:
                    result.append(name)
            elif self.options.no_package:
                if name not in self.options.no_package:
                    result.append(name)
            elif self.options.type == "indep":
                if ptype == "indep":
                    result.append(name)
            elif self.options.type == "arch":
                if ptype == "arch":
                    result.append(name)
            elif self.options.type == "both":
                result.append(name)

        return result

    def get_main_package(self):
        if self.options.mainpackage:
            return self.options.mainpackage
        else:
            with open("debian/control", "r") as f:
                source, packages = deb822.read_control(f)

            return packages[0]["package"]

    def get_package_file(self, package, extension):
        paths = [
            os.path.join("debian", package + "." + extension),
        ]

        if package == self.get_main_package():
            paths.append(os.path.join("debian", extension))

        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def read_package_file(self, package, extension):
        path = self.get_package_file(package, extension)
        if path is None:
            return None
        elif os.access(path, os.X_OK):
            return io.StringIO(subprocess.check_output(
                [os.path.abspath(path)]).decode("utf-8"))
        else:
            return open(path, "r")

    def get_build_directory(self):
        return self.options.builddirectory

    def get_tmpdir(self, package):
        if self.options.tmpdir:
            return self.options.tmpdir
        else:
            return os.path.join("debian", package)

    def write_substvar(self, name, value, package=None):
        if package:
            filename = "debian/%s.substvars" % package
        else:
            filename = "debian/substvars"

        line = "%s=%s" % (name, value)
        self.print_cmd(["echo", line, ">>", filename])
        if not self.options.no_act:
            with open(filename, "a") as f:
                print(line, file=f)

    def log_installed_files(self, package, paths):
        if self.options.no_act:
            return
        pkgdir = "debian/.debhelper/generated/%s" % package
        os.makedirs(pkgdir, exist_ok=True)
        with open(os.path.join(pkgdir, "installed-by-%s" % self.tool_name),
                  "a") as f:
            for p in paths:
                f.write("%s\n" % p)

    def do_cmake_install(self, builddir, package, component=None, subdir=None,
                         extra_args=None):
        build_subdir = builddir
        if subdir:
            build_subdir = os.path.join(builddir, subdir)
        args = ["cmake", "--install", build_subdir]
        if component:
            args += ["--component", component]
        if extra_args:
            args += extra_args
        env = os.environ.copy()
        env["DESTDIR"] = os.path.abspath(self.get_tmpdir(package))
        self.do_cmd(args, env=env)

        if component:
            install_manifest = "install_manifest_%s.txt" % component
        else:
            install_manifest = "install_manifest.txt"
        have_manifest = True
        try:
            with open(os.path.join(builddir, install_manifest)) as f:
                files = [os.path.join(self.options.sourcedir,
                                      os.path.relpath(l.rstrip("\n"), "/"))
                         for l in f]
        except FileNotFoundError:
            have_manifest = False
        if have_manifest:
            os.unlink(os.path.join(builddir, install_manifest))
            self.log_installed_files(package, files)
