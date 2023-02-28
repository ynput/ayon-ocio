import os
import json

from fastapi import Depends

from ayon_server.addons import BaseServerAddon
from ayon_server.api.dependencies import dep_current_user
from ayon_server.entities import UserEntity

from .version import __version__

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class OCIODistAddon(BaseServerAddon):
    name = "ocio_dist"
    title = "OCIO Distribution"
    version = __version__

    def initialize(self):
        self.add_endpoint(
            "ocio_zip_info",
            self.get_ocio_zip_info,
            method="GET",
        )

    async def get_ocio_zip_info(
        self,
        user: UserEntity = Depends(dep_current_user)
    ) -> dict[str, str]:
        info_filepath = os.path.join(
            CURRENT_DIR, "private", "ocio_zip_info.json"
        )
        with open(info_filepath, "r") as stream:
            data = json.load(info_filepath)
        return data
