import sys
from arcaflow_plugin_sdk import plugin
import arcaflow_plugin_fio.fio_plugin as fio_plugin


def main():
    sys.exit(plugin.run(plugin.build_schema(fio_plugin.run)))


if __name__ == "__main__":
    main()
