# This file is part of dh-cmake, and is distributed under the OSI-approved
# BSD 3-Clause license. See top-level LICENSE file or
# https://gitlab.kitware.com/debian/dh-cmake/blob/master/LICENSE for details.

import json
import os.path
import re

from dhcmake import common


class DHCPack(common.DHCommon):
    def read_cpack_metadata(self):
        with open("debian/.cpack/cpack-metadata.json", "r") as f:
            self.cpack_metadata = json.load(f)

    def get_cpack_components(self, package):
        opened_file = self.read_package_file(package, "cpack-components")
        if opened_file:
            retval = []
            with opened_file as f:
                for l in f:
                    if not re.search("^($|#)", l):
                        group = l.rstrip()
                        if group in self.cpack_metadata["components"]:
                            retval.append(group)
                        else:
                            raise ValueError(
                                "Invalid CPack components in %s" % package)
            return retval
        else:
            return []

    def get_cpack_component_groups(self, package):
        opened_file = self.read_package_file(package, "cpack-component-groups")
        if opened_file:
            retval = []
            with opened_file as f:
                for l in f:
                    if not re.search("^($|#)", l):
                        group = l.rstrip()
                        if group in self.cpack_metadata["componentGroups"]:
                            retval.append(group)
                        else:
                            raise ValueError(
                                "Invalid CPack component groups in %s" %
                                package)
            return retval
        else:
            return []

    def get_all_cpack_components_for_group(self, group, visited=None):
        if visited is None:
            visited = set()

        if group in visited:
            return set()
        visited.add(group)

        all_components = set(self.cpack_metadata["componentGroups"][group]
                             ["components"])

        for sub_group in self.cpack_metadata["componentGroups"][group]["subgroups"]:
            all_components.update(
                self.get_all_cpack_components_for_group(
                    sub_group, visited))

        return all_components

    def get_all_cpack_components(self, package):
        all_components = set(self.get_cpack_components(package))

        for group in self.get_cpack_component_groups(package):
            all_components.update(
                self.get_all_cpack_components_for_group(group))

        return all_components

    def get_package_dependencies(self, package):
        deps = set()

        for component in self.get_all_cpack_components(package):
            for component_dep in self.cpack_metadata["components"][component]["dependencies"]:
                for other_package in self.get_packages():
                    if component_dep in \
                            self.get_all_cpack_components(other_package):
                        deps.add(other_package)

        return deps

    @common.DHEntryPoint("dh_cpack_generate")
    def generate(self, args=None):
        self.parse_args(args)

        cmd_args = [
            "cpack",
            "--config",
            os.path.join(self.get_build_directory(), "CPackConfig.cmake"),
            "-G", "External",
            "-D", "CPACK_PACKAGE_FILE_NAME=cpack-metadata",
            "-D", "CPACK_EXT_REQUESTED_VERSIONS=1.0",
            "-B", "debian/.cpack",
        ]
        self.do_cmd(cmd_args)

    @common.DHEntryPoint("dh_cpack_substvars")
    def substvars(self, args=None):
        self.parse_args(args)
        self.read_cpack_metadata()

        for package in self.get_packages():
            depends = ", ".join(dep + " (= ${binary:Version})" for dep in
                                sorted(self.get_package_dependencies(package)))
            if depends:
                self.write_substvar("cpack:Depends", depends, package)

    def install_make_arg_parser(self, parser):
        self.make_arg_parser(parser)
        parser.add_argument(
            "--sourcedir", action="store",
            help="Source directory for installation (not used except to notify"
                 " dh_missing)",
            default="debian/tmp")

    @common.DHEntryPoint("dh_cpack_install")
    def install(self, args=None):
        self.parse_args(args, make_arg_parser=self.install_make_arg_parser)
        self.read_cpack_metadata()

        for package in self.get_packages():
            for component in self.get_all_cpack_components(package):
                for project in self.cpack_metadata["projects"]:
                    if component in project["components"]:
                        extra_args = []

                        try:
                            extra_args.extend([
                                "--config",
                                self.cpack_metadata["buildType"]
                            ])
                        except KeyError:
                            pass

                        # TODO Fix this in CMake (https://gitlab.kitware.com/cmake/cmake/-/issues/20700)
                        # try:
                        #    extra_args.append(
                        #            "-DCMAKE_INSTALL_DEFAULT_"
                        #            "DIRECTORY_PERMISSIONS:STRING=" +
                        #            self.cpack_metadata[
                        #                "defaultDirectoryPermissions"])
                        # except KeyError:
                        #    pass

                        if self.cpack_metadata["stripFiles"]:
                            extra_args.append("--strip")

                        self.do_cmake_install(
                            project["directory"], package,
                            component=component,
                            extra_args=extra_args)


def generate():
    dhcpack = DHCPack()
    dhcpack.generate()


def substvars():
    dhcpack = DHCPack()
    dhcpack.substvars()


def install():
    dhcpack = DHCPack()
    dhcpack.install()
