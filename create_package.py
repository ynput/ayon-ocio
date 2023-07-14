"""Prepares server package from addon repo to upload to server.

Requires Python 3.9. (Or at least 3.8+).

This script should be called from cloned addon repo.

It will produce 'package' subdirectory which could be pasted into server
addon directory directly (eg. into `ayon-backend/addons`).

Format of package folder:
ADDON_REPO/package/{addon name}/{addon version}

You can specify `--output_dir` in arguments to change output directory where
package will be created. Existing package directory will always be purged if
already present! This could be used to create package directly in server folder
if available.

Package contains server side files directly,
client side code zipped in `private` subfolder.
"""

import os
import sys
import re
import platform
import shutil
import argparse
import logging
import collections
import zipfile
import hashlib
import urllib.request


ADDON_NAME = "ayon_ocio"
ADDON_CLIENT_DIR = "ayon_ocio"

# Patterns of directories to be skipped for server part of addon
IGNORE_DIR_PATTERNS = [
    re.compile(pattern)
    for pattern in {
        # Skip directories starting with '.'
        r"^\.",
        # Skip any pycache folders
        "^__pycache__$"
    }
]

# Patterns of files to be skipped for server part of addon
IGNORE_FILE_PATTERNS = [
    re.compile(pattern)
    for pattern in {
        # Skip files starting with '.'
        # NOTE this could be an issue in some cases
        r"^\.",
        # Skip '.pyc' files
        r"\.pyc$"
    }
]


def safe_copy_file(src_path, dst_path):
    """Copy file and make sure destination directory exists.

    Ignore if destination already contains directories from source.

    Args:
        src_path (str): File path that will be copied.
        dst_path (str): Path to destination file.
    """

    if src_path == dst_path:
        return

    dst_dir = os.path.dirname(dst_path)
    try:
        os.makedirs(dst_dir)
    except Exception:
        pass

    shutil.copy2(src_path, dst_path)


def _value_match_regexes(value, regexes):
    for regex in regexes:
        if regex.search(value):
            return True
    return False


def find_files_in_subdir(
    src_path,
    ignore_file_patterns=None,
    ignore_dir_patterns=None
):
    if ignore_file_patterns is None:
        ignore_file_patterns = IGNORE_FILE_PATTERNS

    if ignore_dir_patterns is None:
        ignore_dir_patterns = IGNORE_DIR_PATTERNS
    output = []

    hierarchy_queue = collections.deque()
    hierarchy_queue.append((src_path, []))
    while hierarchy_queue:
        item = hierarchy_queue.popleft()
        dirpath, parents = item
        for name in os.listdir(dirpath):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path):
                if not _value_match_regexes(name, ignore_file_patterns):
                    items = list(parents)
                    items.append(name)
                    output.append((path, os.path.sep.join(items)))
                continue

            if not _value_match_regexes(name, ignore_dir_patterns):
                items = list(parents)
                items.append(name)
                hierarchy_queue.append((path, items))

    return output


def copy_server_content(addon_output_dir, current_dir, log):
    """Copies server side folders to 'addon_package_dir'

    Args:
        addon_output_dir (str): package dir in addon repo dir
        current_dir (str): addon repo dir
        log (logging.Logger)
    """

    log.info("Copying server content")

    filepaths_to_copy = []
    server_dirpath = os.path.join(current_dir, "server")

    # Version
    src_version_path = os.path.join(current_dir, "version.py")
    dst_version_path = os.path.join(addon_output_dir, "version.py")
    filepaths_to_copy.append((src_version_path, dst_version_path))

    for item in find_files_in_subdir(server_dirpath):
        src_path, dst_subpath = item
        dst_path = os.path.join(addon_output_dir, dst_subpath)
        filepaths_to_copy.append((src_path, dst_path))

    # Copy files
    for src_path, dst_path in filepaths_to_copy:
        safe_copy_file(src_path, dst_path)


def download_ocio_zip(current_dir, log):
    filename = "OpenColorIO-Configs-1.0.2.zip"
    src_url = "https://distribute.openpype.io/thirdparty/{}".format(filename)
    checksum = "51285a1350b31855f831d12d30ede727"  # md5

    download_dir = os.path.join(current_dir, "downloads")
    ocio_zip_path = os.path.join(download_dir, filename)

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    if os.path.exists(ocio_zip_path):
        with open(ocio_zip_path, "rb") as stream:
            file_checksum = hashlib.md5(stream.read()).hexdigest()
        if checksum == file_checksum:
            log.debug(f"OCIO zip is already downloaded {ocio_zip_path}")
            return ocio_zip_path

    log.debug(f"OCIO zip from {src_url} -> {ocio_zip_path}")

    log.info("OCIO zip download - started")
    urllib.request.urlretrieve(src_url, ocio_zip_path)
    log.info("OCIO zip download - finished")
    return ocio_zip_path


class ZipFileLongPaths(zipfile.ZipFile):
    """Allows longer paths in zip files.

    Regular DOS paths are limited to MAX_PATH (260) characters, including
    the string's terminating NUL character.
    That limit can be exceeded by using an extended-length path that
    starts with the '\\?\' prefix.
    """
    _is_windows = platform.system().lower() == "windows"

    def _extract_member(self, member, tpath, pwd):
        if self._is_windows:
            tpath = os.path.abspath(tpath)
            if tpath.startswith("\\\\"):
                tpath = "\\\\?\\UNC\\" + tpath[2:]
            else:
                tpath = "\\\\?\\" + tpath

        return super(ZipFileLongPaths, self)._extract_member(
            member, tpath, pwd
        )


def zip_client_side(addon_output_dir, current_dir, log):
    """Copy and zip `client` content into 'addon_package_dir'.

    Args:
        addon_output_dir (str): Output package directory path.
        current_dir (str): Directory path of addon source.
        log (logging.Logger): Logger object.
    """

    client_dir = os.path.join(current_dir, "client")
    if not os.path.isdir(client_dir):
        raise ValueError("Client directory was not found. Skipping")

    log.info("Preparing client code zip")
    private_dir = os.path.join(addon_output_dir, "private")

    if not os.path.exists(private_dir):
        os.makedirs(private_dir)

    ocio_zip_path = download_ocio_zip(current_dir, log)
    src_version_path = os.path.join(current_dir, "version.py")
    dst_version_path = os.path.join(ADDON_CLIENT_DIR, "version.py")

    zip_filepath = os.path.join(os.path.join(private_dir, "client.zip"))
    with ZipFileLongPaths(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add client code content to zip
        for path, sub_path in find_files_in_subdir(client_dir):
            zipf.write(path, sub_path)

        # Add 'version.py' to client code
        zipf.write(src_version_path, dst_version_path)

        # Add OCIO configs to client code
        with ZipFileLongPaths(ocio_zip_path) as ocio_zip:
            for path_item in ocio_zip.infolist():
                if path_item.is_dir():
                    continue
                src_path = path_item.filename
                dst_path = os.path.join(
                    ADDON_CLIENT_DIR, "configs", src_path)
                zipf.writestr(dst_path, ocio_zip.read(src_path))


def main(output_dir=None):
    log = logging.getLogger("create_package")
    log.info("Start creating package")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not output_dir:
        output_dir = os.path.join(current_dir, "package")

    version_filepath = os.path.join(current_dir, "version.py")
    version_content = {}
    with open(version_filepath, "r") as stream:
        exec(stream.read(), version_content)
    addon_version = version_content["__version__"]

    new_created_version_dir = os.path.join(
        output_dir, ADDON_NAME, addon_version
    )
    if os.path.isdir(new_created_version_dir):
        log.info(f"Purging {new_created_version_dir}")
        shutil.rmtree(output_dir)

    log.info(f"Preparing package for {ADDON_NAME}-{addon_version}")

    addon_output_dir = os.path.join(output_dir, ADDON_NAME, addon_version)
    if not os.path.exists(addon_output_dir):
        os.makedirs(addon_output_dir)

    copy_server_content(addon_output_dir, current_dir, log)

    zip_client_side(addon_output_dir, current_dir, log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_dir",
        help=(
            "Directory path where package will be created"
            " (Will be purged if already exists!)"
        )
    )

    args = parser.parse_args(sys.argv[1:])
    main(args.output_dir)
