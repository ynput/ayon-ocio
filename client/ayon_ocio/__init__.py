import os

from ayon_core.addon import AYONAddon

from .version import __version__

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_ROOT = os.path.join(CURRENT_DIR, "configs")


class OCIODistAddon(AYONAddon):
    """OCIO addon to deploy default OCIO configs.

    OCIO zip is on server and can be downloaded from there. That won't be part
    of client build as it's quite big dependency that doesn't need update on
    each client build update.
    """

    name = "ayon_ocio"
    version = __version__

    def get_global_environments(self):
        return {
            "BUILTIN_OCIO_ROOT": self.get_ocio_config_dir()
        }

    @classmethod
    def get_ocio_config_dir(cls):
        """Get OCIO config dir and download then if are not available.

        Returns:
            str: Path to OCIO config directory.
        """

        return os.path.join(
            CONFIG_ROOT
        )


def get_ocio_config_path():
    return OCIODistAddon.get_ocio_config_dir()
