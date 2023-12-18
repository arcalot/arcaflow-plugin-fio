import sys
from arcaflow_plugin_sdk import plugin
import fio_plugin

if __name__ == "__main__":
    sys.exit(plugin.run(plugin.build_schema(fio_plugin.run)))
