#!/usr/bin/env python3

import unittest
import json
import sys
import yaml
from pathlib import Path
import fio_plugin
import fio_schema
from arcaflow_plugin_sdk import plugin

with open("../fixtures/poisson-rate-submission_output-plus.json", "r") as fout:
    poisson_submit_outfile = fout.read()

poisson_submit_output = json.loads(poisson_submit_outfile)

with open("../fixtures/poisson-rate-submission_input.yaml", "r") as fin:
    poisson_submit_infile = fin.read()

poisson_submit_input = fio_schema.fio_input_schema.unserialize(
    yaml.safe_load(poisson_submit_infile)
)


class FioPluginTest(unittest.TestCase):
    @staticmethod
    def test_serialization():
        plugin.test_object_serialization(
            fio_schema.fio_input_schema.unserialize(
                yaml.safe_load(poisson_submit_infile)
            )
        )

        plugin.test_object_serialization(
            fio_plugin.fio_output_schema.unserialize(poisson_submit_output)
        )

    def test_functional_success(self):
        input = fio_schema.fio_input_schema.unserialize(
            yaml.safe_load(poisson_submit_infile)
        )
        input.cleanup = False
        output_id, output_data = fio_plugin.run(
            params=input, run_id="plugin_ci"
        )

        try:
            self.assertEqual(output_id, "success")
            self.assertEqual(
                output_data.jobs[0].jobname, "poisson-rate-submit"
            )
            self.assertEqual(output_data.jobs[0].job_options["iodepth"], "32")
            self.assertEqual(output_data.jobs[0].job_options["size"], "100KiB")
            self.assertAlmostEqual(output_data.jobs[0].elapsed, 2, delta=1)
            self.assertAlmostEqual(
                output_data.jobs[0].read.runtime, 2000, delta=10
            )
        except AssertionError:
            sys.stderr.write("Error: {}\n".format(output_data.error))
            raise

        Path("fio-input-tmp.fio").unlink(missing_ok=True)
        Path(input.jobs[0].name + ".0.0").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
