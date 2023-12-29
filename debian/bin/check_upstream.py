#!/usr/bin/env python3

import errno, filecmp, fnmatch, glob, os.path, re, sys
from debian import deb822
from enum import Enum
import hashlib
import argparse
import pathlib

sys.path.insert(0, "debian/lib/python")
rules_defs = dict(
    (match.group(1), match.group(2))
    for line in open("debian/rules.defs")
    for match in [re.match(r"(\w+)\s*:=\s*(.*)\n", line)]
)
sys.path.append("/usr/share/linux-support-%s/lib/python" % rules_defs["KERNELVERSION"])
from debian_linux.firmware import FirmwareWhence
from config import Config


class DistState(Enum):
    undistributable = 1
    non_free = 2
    free = 3


def is_source_available(section):
    for file_info in section.files.values():
        if not (file_info.source or file_info.binary.endswith(".cis")):
            return False
    return True


def check_section(section):
    if re.search(
        r"^BSD\b"
        r"|^GPLv2 or OpenIB\.org BSD\b"
        r"|\bPermission\s+is\s+hereby\s+granted\s+for\s+the\s+"
        r"distribution\s+of\s+this\s+firmware\s+(?:data|image)\b"
        r"(?!\s+as\s+part\s+of)"
        r"|\bRedistribution\s+and\s+use\s+in(?:\s+source\s+and)?"
        r"\s+binary\s+forms\b"
        r"|\bPermission\s+is\s+hereby\s+granted\b[^.]+\sto"
        r"\s+deal\s+in\s+the\s+Software\s+without"
        r"\s+restriction\b"
        r"|\bredistributable\s+in\s+binary\s+form\b"
        r"|\bFree software. See LICENCE.open-ath9k-htc-firmware for details\b",
        section.licence,
    ):
        return DistState.free if is_source_available(section) else DistState.non_free
    elif re.match(r"^(?:D|Red)istributable\b", section.licence):
        return DistState.non_free
    elif re.match(r"^GPL(?:v[23]|\+)?\b|^Dual GPL(?:v[23])?/", section.licence):
        return (
            DistState.free
            if is_source_available(section)
            else DistState.undistributable
        )
    else:
        # Unrecognised and probably undistributable
        return DistState.undistributable


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def update_file(source_dir, over_dirs, filename):
    source_file = os.path.join(source_dir, filename)
    for over_dir in over_dirs:
        for over_file in [os.path.join(over_dir, filename)] + glob.glob(
            os.path.join(over_dir, filename + "-*")
        ):
            if os.path.isfile(over_file):
                if not filecmp.cmp(source_file, over_file, True):
                    print("I: %s: changed" % filename)
                return


def get_exclusions():
    with open("debian/copyright") as f:
        return deb822.Deb822(f).get("Files-Excluded", "").strip().split()


def get_packaged_files(config):
    packaged_files = {}
    for package in config["base",]["packages"]:
        for filename in config["base", package]["files"]:
            packaged_files[filename] = package
    return packaged_files


def get_ignored_files(config):
    ignored_files = {}
    for package in config["base",]["packages"]:
        for ignored_file in config["base", package].get("ignore-files", []):
            if m := re.match(r"^(.*)=(\S+)\s*$", ignored_file):
                ignored_file = m.group(1)
                ignored_md5sum = m.group(2)
            else:
                print(
                    "E: missing md5sum in ignore_files of package %s: %s"
                    % (package, ignored_file)
                )
                continue
            if ignored_file not in ignored_files:
                ignored_files[ignored_file] = {}
            ignored_files[ignored_file][ignored_md5sum] = package
    return ignored_files


def file_ignored(filename, ignored_files):
    if filename in ignored_files:
        # check md5sum against explicitly ignored files
        file_md5 = md5(filename)
        if file_md5 in ignored_files[filename]:
            print("I: ignoring %s=%s" % (filename, file_md5))
            return True
        else:
            print("W: new md5sum for ignored file %s=%s" % (filename, file_md5))
    return False


def get_upstream_installed(source_dir):
    upstream_installed = {}
    upstream_install_path = pathlib.Path(source_dir + "/debian/build/install").resolve()
    for installed_item in upstream_install_path.rglob("*"):
        installed_item_base = installed_item.relative_to(upstream_install_path)
        if installed_item.is_symlink():
            ltarget = installed_item.resolve()
            ltarget_rel = ltarget.relative_to(upstream_install_path)
            if not ltarget.exists():
                # print("symlink_dangling: %s -> %s" % (installed_item_base, ltarget_rel))
                upstream_installed[installed_item_base] = None
            elif ltarget.is_dir():
                # print("symlink_dir: %s -> %s" % (installed_item_base, ltarget_rel))
                upstream_installed[installed_item_base] = ltarget_rel
            elif ltarget.is_file():
                # print("symlink_file: %s -> %s" % (installed_item_base, ltarget_rel))
                upstream_installed[installed_item_base] = ltarget_rel
            else:
                # print("symlink_other: %s -> %s" % (installed_item_base, ltarget_rel))
                upstream_installed[installed_item_base] = ltarget_rel
        elif installed_item.is_file():
            upstream_installed[installed_item_base] = installed_item_base
    return upstream_installed


def get_debian_installed(source_dir, config):
    debian_installed = {}
    for package in config["base",]["packages"]:
        package_path = pathlib.Path(source_dir + "/debian/firmware-" + package).resolve()
        if not package_path.is_dir():
            print("E: missing debian package path %s" % (package_path))
            continue
        package_install_path = package_path / "lib/firmware"
        if not package_install_path.is_dir():
            package_install_path = package_path / "usr/lib/firmware"
            if not package_install_path.is_dir():
                print("E: debian/firmware-%s contains neither " +
                      "lib/firmware nor usr/lib/firmware")
                continue
        for packaged_item in package_install_path.rglob("*"):
            packaged_item_base = packaged_item.relative_to(package_install_path)
            debian_installed[packaged_item_base] = package
    return debian_installed


def check_whence(source_dir, show_licence):
    config = Config()
    exclusions = get_exclusions()
    packaged_files = get_packaged_files(config)
    ignored_files = get_ignored_files(config)

    over_dirs = ["debian/config/" + package for package in config["base",]["packages"]]
    for section in FirmwareWhence(open(os.path.join(source_dir, "WHENCE"))):
        dist_state = check_section(section)
        for file_info in section.files.values():
            if file_ignored(file_info.binary, ignored_files):
                continue

            if dist_state == DistState.non_free:
                if not any(fnmatch.fnmatch(file_info.binary, e) for e in exclusions):
                    if file_info.binary in packaged_files:
                        update_file(source_dir, over_dirs, file_info.binary)
                    elif os.path.isfile(file_info.binary):
                        print(
                            "I: %s is not included in any binary package"
                            % file_info.binary
                        )
                    else:
                        print("I: %s: could be added" % file_info.binary)
            elif dist_state == DistState.undistributable:
                if file_info.binary in packaged_files:
                    # if file was packaged, someone must have manually checked licence
                    update_file(source_dir, over_dirs, file_info.binary)
                elif os.path.isfile(file_info.binary):
                    print("W: %s appears to be undistributable" % file_info.binary)
                    if show_licence:
                        print("D: Licence:")
                        for line in section.licence.splitlines():
                            print("D:  %s" % (line))
                        print("")


def check_build(source_dir):
    config = Config()
    exclusions = get_exclusions()
    packaged_files = get_packaged_files(config)
    ignored_files = get_ignored_files(config)

    upstream_installed = get_upstream_installed(source_dir)
    debian_installed = get_debian_installed(source_dir, config)

    for upstream_item in sorted(upstream_installed.keys()):
        debian_item = debian_installed.get(upstream_item, None)
        if debian_item is not None:
            continue
        if file_ignored(str(upstream_item), ignored_files):
            continue
        if any(fnmatch.fnmatch(upstream_item, e) for e in exclusions):
            continue
        upstream_file = upstream_installed[upstream_item]
        if upstream_file is None:
            print("I: ignoring dangling symlink in upstream: %s" % (upstream_item))
            continue
        if upstream_item == upstream_file:
            print("missing    file from packaging: %s" % (upstream_item))
            continue
        # symlink
        target_package = debian_installed.get(upstream_file, None)
        if target_package is None:
            print("missing symlink from packaging: %s (package together with: %s)" % (
                upstream_item, upstream_file))
        else:
            print("missing symlink from packaging: %s (suggested target pkg: %s)" % (
                upstream_item, str(target_package)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check debian package against upstream changes"
    )
    parser.add_argument(
        "--show_licence",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Display licence for undistributable files",
    )
    parser.add_argument(
        "--build",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Perform the checks after building the packages",
    )
    parser.add_argument(
        "source_dir",
        nargs="?",
        default=".",
        help="Path to the firmware-nonfree package source directory",
    )
    args = vars(parser.parse_args())
    if args["build"]:
        check_build(args["source_dir"])
    else:
        check_whence(args["source_dir"], args["show_licence"])
