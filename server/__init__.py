import os

from ayon_server.addons import BaseServerAddon

from .version import __version__

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


class OCIODistAddon(BaseServerAddon):
    name = "ayon_ocio"
    title = "OCIO Distribution"
    version = __version__
