import sys
# from arcaflow_plugin_sdk import plugin
# import arcaflow_plugin_fio.fio_plugin as fio_plugin
from arcaflow_plugin_fio import main


if __name__ == "__main__":
    main.main()
    # print('=================')
    # print('sys modules')
    # for key in sys.modules:
    #     print(key)
    # # print(sys.modules['builtin'])
    # print(sys.modules['arcaflow_plugin_fio'])
    # print(sys.modules['arcaflow_plugin_fio.fio_plugin'])
    # sys.exit(plugin.run(plugin.build_schema(fio_plugin.run)))


