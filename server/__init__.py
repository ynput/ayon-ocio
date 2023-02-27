import os

from fastapi import Depends

from ayon_server.addons import BaseServerAddon
from ayon_server.api.dependencies import dep_current_user
from ayon_server.entities import UserEntity

from .version import __version__

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class MyAddon(BaseServerAddon):
    name = "ocio_dist"
    title = "OCIO Distribution"
    version = __version__

    def initialize(self):
        self.add_endpoint(
            "ocio-file-hash",
            self.get_ocio_file_hash,
            method="GET",
        )

    async def get_ocio_file_hash(
        self,
        user: UserEntity = Depends(dep_current_user)
    ):
        hash_filepath = os.path.join(CURRENT_DIR, "private", "ocio_zip_hash")
        with open(hash_filepath, "r") as stream:
            filehash = stream.read()
        return filehash
