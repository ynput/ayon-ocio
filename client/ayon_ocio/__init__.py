import os
import json
import hashlib
import shutil
import zipfile

import ayon_api
from openpype.modules import OpenPypeModule, ITrayModule
from .version import __version__

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(CURRENT_DIR, "vendor")


class OCIODistModule(OpenPypeModule, ITrayModule):
    """OCIO addon to deploy default OCIO configs.

    OCIO zip is on server and can be downloaded from there. That won't be part
    of client build as it's quite big dependency that doesn't need update on
    each client build update.
    """

    name = "ocio_dist"
    version = __version__
    # Class cache if download is needed
    _download_needed = True

    def initialize(self, module_settings):
        self.enabled = True

    def tray_exit(self):
        pass

    def tray_menu(self, tray_menu):
        pass

    def tray_init(self):
        pass

    def tray_start(self):
        pass

    @classmethod
    def get_server_ocio_file_info(cls):
        """Receive zip file info from server.

        Information must contain at least 'filename' and 'hash' with md5 zip
        file hash.

        Returns:
            dict[str, str]: Information about zip file from server.
        """

        response = ayon_api.get("addons/{}/{}/ocio_zip_info".format(
            cls.name, cls.version
        ))
        response.raise_for_status()
        return response.data

    @classmethod
    def get_ocio_vendor_dir(cls):
        """Dir path where ocio files are downloaded."""

        return VENDOR_DIR

    @classmethod
    def get_ocio_config_dir(cls, check_download=True):
        """Get OCIO config dir and download then if are not available.

        Args:
            check_download (bool): Check if config is downloaded and download
                them if are not available.

        Returns:
            str: Path to OCIO config directory.
        """

        if check_download and cls.is_download_needed():
            cls.download_ocio_file()
        return os.path.join(
            cls.get_ocio_vendor_dir(),
            "OpenColorIOConfigs"
        )

    @classmethod
    def get_ocio_zip_info_path(cls):
        """Path to file where zip info is stored on download.

        The content has downloaded filename and hash of file that can be
        compared to server hash to validate if are the same.

        Returns:
            str: Path to zip info file.
        """

        return os.path.join(cls.get_ocio_vendor_dir(), "ocio_file_info.json")

    @classmethod
    def is_download_needed(cls):
        """Check if is download needed.

        Returns:
            bool: Should be config downloaded.
        """

        if not cls._download_needed:
            return False

        dirpath = cls.get_ocio_vendor_dir()
        if not os.path.exists(dirpath):
            return True

        ocio_config_dir = cls.get_ocio_config_dir(False)
        file_info_path = cls.get_ocio_zip_info_path()
        if (
            not os.path.exists(file_info_path)
            or not os.path.exists(ocio_config_dir)
        ):
            return True

        with open(file_info_path, "r") as stream:
            file_info = json.load(stream)

        result = cls.get_server_ocio_file_info()
        if result["hash"] == file_info["hash"]:
            cls._download_needed = False
        return cls._download_needed

    @classmethod
    def download_ocio_file(cls, progress=None):
        """Download OCIO file from server.

        Todos:
            Add safeguard to avoid downloading of the file from multiple
                processes at once.

        Args:
            progress (ayon_api.TransferProgress): Keep track about download.
        """

        dirpath = cls.get_ocio_vendor_dir()
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        else:
            for name in tuple(os.listdir(dirpath)):
                path = os.path.join(dirpath, name)
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(os.path.join(dirpath, name))

        file_info = cls.get_server_ocio_file_info()
        filename = file_info["filename"]
        server_hash = file_info["hash"]
        zip_filepath = os.path.join(dirpath, filename)
        endpoint = "{}/addons/{}/{}/private/{}".format(
            ayon_api.get_base_url(), cls.name, cls.version, filename
        )
        ayon_api.download_file(endpoint, zip_filepath, progress=progress)
        with open(zip_filepath, "rb") as stream:
            zipfile_hash = hashlib.md5(stream.read()).hexdigest()

        if server_hash != zipfile_hash:
            raise ValueError(
                "Downloaded file hash does not match expected hash"
            )

        with zipfile.ZipFile(zip_filepath, "r") as zfile:
            zfile.extractall(dirpath)

        file_info_path = cls.get_ocio_zip_info_path()
        with open(file_info_path, "w") as stream:
            json.dump(file_info, stream)
        os.remove(zip_filepath)
        cls._download_needed = False


def get_ocio_config_path():
    return OCIODistModule.get_ocio_config_dir()
