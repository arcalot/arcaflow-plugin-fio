#!/usr/bin/env python3

import sys
import typing
import json
import subprocess
from traceback import format_exc
from typing import Union
from pathlib import Path

from arcaflow_plugin_sdk import plugin
from fio_schema import (
    FioInput,
    FioSuccessOutput,
    FioErrorOutput,
    fio_output_schema,
)


def split_json_and_errors(fio_output: str):
    # Sometimes fio informational messages are included at the top of the JSON output.
    # Separate the json data from the errors and return them as a tuple.
    error_data = ""
    lines = fio_output.splitlines()
    for i in range(len(fio_output)):
        file_data = "\n".join(lines[i:])
        try:
            json_data = json.loads(file_data)
            break
        except json.JSONDecodeError:
            error_data += f"{lines[i]}\n"
            continue

    return json_data, str(error_data)


@plugin.step(
    id="workload",
    name="fio workload",
    description="run an fio workload",
    outputs={"success": FioSuccessOutput, "error": FioErrorOutput},
)
def run(
    params: FioInput,
) -> typing.Tuple[str, Union[FioSuccessOutput, FioErrorOutput]]:
    try:
        infile_temp_path = Path("fio-input-tmp.fio")
        params.write_jobs_to_file(infile_temp_path)
        cmd = [
            "fio",
            infile_temp_path,
            "--output-format=json+",
        ]

        cmd_out = subprocess.check_output(
            args=cmd,
            stderr=subprocess.STDOUT,
            text=True,
        )

        json_data, error_data = split_json_and_errors(cmd_out)

        # It is possible for fio to complete successfully but still return some
        # informational messages. If we have any, raise them for debug output.
        if error_data:
            print(f"fio messages:\n{error_data}")

        output: FioSuccessOutput = fio_output_schema.unserialize(json_data)

        return "success", output

    except FileNotFoundError as exc:
        if exc.filename == "fio":
            error_output: FioErrorOutput = FioErrorOutput(
                "missing fio executable, please install fio package"
            )
        else:
            error_output: FioErrorOutput = FioErrorOutput(format_exc())
        return "error", error_output

    except subprocess.CalledProcessError as err:
        # Get the error messages only from the output
        _, error_data = split_json_and_errors(err.output)
        return "error", FioErrorOutput(
            f"{err.cmd[0]} failed with return code {err.returncode}:\n{error_data}"
        )

    finally:
        if params.cleanup:
            infile_temp_path.unlink(missing_ok=True)
            for job in params.jobs:
                Path(job.name + ".0.0").unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(plugin.run(plugin.build_schema(run)))
