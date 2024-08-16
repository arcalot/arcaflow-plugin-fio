#!/usr/bin/env python3

import typing
import enum
import configparser
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict
from pathlib import Path

from arcaflow_plugin_sdk import plugin, schema, validation


class IoPattern(str, enum.Enum):
    read = "read"
    write = "write"
    randread = "randread"
    randwrite = "randwrite"
    rw = "rw"
    readwrite = "readwrite"
    randrw = "randrw"
    # trimwrite = 'trimwrite' # WIP
    # randtrim = 'randtrim' # WIP

    def __str__(self) -> str:
        return self.value


class RateProcess(str, enum.Enum):
    linear = "linear"
    poisson = "poisson"

    def __str__(self) -> str:
        return self.value


class IoSubmitMode(str, enum.Enum):
    inline = "inline"
    offload = "offload"

    def __str__(self) -> str:
        return self.value


class IoEngine(str, enum.Enum):
    _sync_io_engines = {"sync", "psync"}
    _async_io_engines = {"libaio", "windowsaio"}
    sync = "sync"
    psync = "psync"
    libaio = "libaio"
    windowsaio = "windowsaio"

    def __str__(self) -> str:
        return self.value

    def is_sync(self) -> bool:
        return self.value in self._sync_io_engines


@dataclass
class JobParams:
    size: typing.Annotated[
        typing.Optional[str],
        validation.min(2),
        schema.name("size"),
        schema.description(
            "The total size of file I/O for each thread of this job. Fio will run "
            "until this many bytes has been transferred, unless runtime is altered by "
            "other means such as (1) runtime, (2) io_size, (3) number_ios, (4) "
            "gaps/holes while doing I/O's such as `rw=read:16K', or (5) sequential "
            "I/O reaching end of the file which is possible when percentage_random is "
            "less than 100. Fio will divide this size between the available files "
            "determined by options such as nrfiles, filename, unless filesize is "
            "specified by the job. If the result of division happens to be 0, the size "
            "is set to the physical size of the given files or devices if they exist. "
            "If this option is not specified, fio will use the full size of the given "
            "files or devices. If the files do not exist, size must be given. It is "
            "also  possible to give size as a percentage between 1 and 100. If "
            "'size=20%' is given, fio will use 20% of the full size of the given files "
            "or devices. In ZBD mode, size can be given in units of number of zones "
            "using 'z'. Can be combined with offset to constrain the start and end "
            "range that I/O will be done within."
        ),
    ] = None
    blocksize: typing.Annotated[
        typing.Optional[str],
        validation.min(2),
        schema.name("Block Size"),
        schema.description(
            "Block size in bytes used for I/O units. Default is 4096. A single value "
            "applies to reads, writes, and trims. Comma-separated values may be "
            "specified for reads, writes, and trims. A value not terminated in a comma "
            "applies to subsequent types."
        ),
    ] = None
    blocksize_range: typing.Annotated[
        typing.Optional[str],
        validation.min(2),
        schema.name("Block Size Range"),
        schema.description(
            "A range of block sizes in bytes for I/O units. The issued I/O unit will "
            "always be a multiple of the minimum size, unless blocksize_unaligned is "
            "set. Comma-separated ranges may be specified for reads, writes, and trims "
            "as described in blocksize."
        ),
    ] = None
    direct: typing.Annotated[
        typing.Optional[int],
        validation.min(0),
        validation.max(1),
        schema.name("Direct I/O"),
        schema.description(
            "Use non-buffered I/O. This is usually O_DIRECT. Note that OpenBSD and ZFS "
            "on Solaris don't support direct I/O. On Windows the synchronous ioengines "
            "don't support direct I/O."
        ),
    ] = None
    numjobs: typing.Annotated[
        typing.Optional[int],
        schema.name("Number of Job Clones"),
        schema.description(
            "Create the specified number of clones of this job. Each clone of job is "
            "spawned as an independent thread or process. May be used to setup a "
            "larger number of threads/processes doing the same thing. Each thread is "
            "reported separately."
        ),
    ] = None
    runtime: typing.Annotated[
        typing.Optional[str],
        schema.name("Job Run Time"),
        schema.description(
            "Limit runtime. The test will run until it completes the configured I/O "
            "workload or until it has run for this specified amount of time, whichever "
            "occurs first. When the unit is omitted, the value is interpreted in "
            "seconds."
        ),
    ] = None
    startdelay: typing.Annotated[
        typing.Optional[str],
        schema.name("Job Start Delay"),
        schema.description(
            "Delay the start of job for the specified amount of time. Can be a single "
            "value or a range. When given as a range, each thread will choose a value "
            "randomly from within the range. Value is in seconds if a unit is omitted."
        ),
    ] = None
    ioengine: typing.Annotated[
        typing.Optional[IoEngine],
        schema.name("IO Engine"),
        schema.description("Defines how the job issues IO to the file."),
    ] = None
    iodepth: typing.Annotated[
        typing.Optional[int],
        schema.name("IO Depth"),
        schema.description(
            "number of IO units to keep in flight against the file."
        ),
    ] = None
    rate_iops: typing.Annotated[
        typing.Optional[int],
        schema.name("IOPS Cap"),
        schema.description("maximum allowed rate of IO operations per second"),
    ] = None
    io_submit_mode: typing.Annotated[
        typing.Optional[IoSubmitMode],
        schema.name("IO Submit Mode"),
        schema.description("Controls how fio submits IO to the IO engine."),
    ] = None
    buffered: typing.Annotated[
        Optional[int],
        validation.min(0),
        validation.max(1),
        schema.name("Buffered"),
        schema.description("Use buffered IO if True, else use direct IO."),
    ] = None
    readwrite: typing.Annotated[
        typing.Optional[IoPattern],
        schema.name("Read/Write"),
        schema.description("type of IO pattern"),
    ] = None
    rate_process: typing.Annotated[
        typing.Optional[RateProcess],
        schema.name("Rate Process"),
        schema.description(
            "Controls the distribution of delay between IO submissions."
        ),
    ] = None


@dataclass
class FioJob:
    name: typing.Annotated[
        str,
        validation.min(1),
        schema.name("Job Name"),
        schema.description("The user-defined name of the fio job."),
    ]
    params: typing.Annotated[
        JobParams,
        schema.name("Fio Job Parameters"),
        schema.description("Parameters to execute one fio job."),
    ]


@dataclass
class FioInput:
    jobs: typing.Annotated[
        typing.List[FioJob],
        schema.name("Fio Jobs List"),
        schema.description("List of jobs for fio to run"),
    ]

    cleanup: typing.Annotated[
        typing.Optional[bool],
        schema.name("Cleanup"),
        schema.description(
            "Cleanup temporary files created during execution."
        ),
    ] = False

    def write_jobs_to_file(self, filepath: Path):
        cfg = configparser.ConfigParser()
        for job in self.jobs:
            cfg[job.name] = {}
            for key, value in asdict(job.params).items():
                if value is not None:
                    cfg[job.name][key] = str(value)
        with open(filepath, "w") as temp:
            cfg.write(
                temp,
                space_around_delimiters=False,
            )


@dataclass
class IoLatency:
    min_: int = field(
        metadata={
            "id": "min",
            "name": "IO Latency Min",
            "description": "IO latency minimum",
        }
    )
    max_: int = field(
        metadata={
            "id": "max",
            "name": "IO Latency Max",
            "description": "IO latency maximum",
        }
    )
    mean: float = field(
        metadata={
            "name": "IO Latency Mean",
            "description": "IO latency mean",
        }
    )
    stddev: float = field(
        metadata={
            "name": "IO Latency StdDev",
            "description": "IO latency standard deviation",
        }
    )
    N: int = field(
        metadata={
            "name": "IO Latency Sample Quantity",
            "description": "quantity of IO latency samples collected",
        }
    )
    percentile: Optional[Dict[str, int]] = field(
        default=None,
        metadata={
            "name": "IO Latency Cumulative Distribution",
            "description": "Cumulative distribution of IO latency sample",
        },
    )
    bins: Optional[Dict[str, int]] = field(
        default=None,
        metadata={
            "name": "Binned IO Latency Sample",
            "description": "binned version of the IO latencies collected",
        },
    )


@dataclass
class SyncIoOutput:
    total_ios: int = field(
        metadata={
            "name": "Quantity of Latencies Logged",
            "description": (
                "Quantity of latency samples collected (i.e. logged)."
            ),
        }
    )
    lat_ns: IoLatency = field(
        metadata={
            "name": "Latency ns",
            "description": "Total latency in nanoseconds.",
        }
    )


@dataclass
class AioOutput:
    io_bytes: int = field(
        metadata={
            "name": "IO B",
            "description": "Quantity of IO transactions in bytes",
        }
    )
    io_kbytes: int = field(
        metadata={
            "name": "IO KiB",
            "description": "Quantity of IO transactions in kibibytes",
        }
    )
    bw_bytes: int = field(
        metadata={
            "name": "Bandwidth B",
            "description": "IO bandwidth used in bytes",
        }
    )
    bw: int = field(
        metadata={
            "name": "Bandwidth KiB",
            "description": "IO bandwidth used in kibibytes",
        }
    )
    iops: float = field(
        metadata={
            "name": "IOPS",
            "description": "IO operations per second",
        }
    )
    runtime: int = field(
        metadata={
            "name": "Runtime",
            "description": "Length of time in seconds on this IO pattern type",
        }
    )
    total_ios: int = field(
        metadata={
            "name": "Quantity of Latencies Logged",
            "description": (
                "Quantity of latency samples collected (i.e. logged)"
            ),
        }
    )
    short_ios: int = field(
        metadata={
            "name": "Short IOs",
            "description": (
                "Unclear from documentation. Educated guess: quantity of"
                " incomplete IO."
            ),
        }
    )
    drop_ios: int = field(
        metadata={
            "name": "Dropped IOs",
            "description": (
                "Unclear from documentation. Edcuated guess: quantity of"
                " dropped IO."
            ),
        }
    )
    slat_ns: IoLatency = field(
        metadata={
            "name": "Submission Latency ns",
            "description": "Submission latency in nanoseconds",
        }
    )
    clat_ns: IoLatency = field(
        metadata={
            "name": "Completion Latency ns",
            "description": "Completion latency in nanoseconds",
        }
    )
    lat_ns: IoLatency = field(
        metadata={
            "name": "Latency ns",
            "description": "Total latency in nanoseconds.",
        }
    )
    bw_min: int = field(
        metadata={
            "name": "Bandwidth Min",
            "description": "Bandwidth minimum",
        }
    )
    bw_max: int = field(
        metadata={
            "name": "Bandwidth Max",
            "description": "Bandwidth maximum",
        }
    )
    bw_agg: float = field(
        metadata={
            "name": "Bandwidth Aggregate Percentile",
            "description": "",
        }
    )
    bw_mean: float = field(
        metadata={
            "name": "Bandwidth Mean",
            "description": "Bandwidth mean",
        }
    )
    bw_dev: float = field(
        metadata={
            "name": "Bandwidth Std Dev",
            "description": "Bandwidth standard deviation",
        }
    )
    bw_samples: int = field(
        metadata={
            "name": "Bandwidth Sample Quantity",
            "description": "Quantity of bandwidth samples collected",
        }
    )
    iops_min: int = field(
        metadata={
            "name": "IOPS Min",
            "description": "IO operations per second minimum",
        }
    )
    iops_max: int = field(
        metadata={
            "name": "IOPS Max",
            "description": "IO operations per second maximum",
        }
    )
    iops_mean: float = field(
        metadata={
            "name": "IOPS Mean",
            "description": "IO operations per second mean",
        }
    )
    iops_stddev: float = field(
        metadata={
            "name": "IOPS Std Dev",
            "description": "IO operations per second standard deviation",
        }
    )
    iops_samples: int = field(
        metadata={
            "name": "IOPS Sample Quantity",
            "description": "Quantity of IOPS samples collected",
        }
    )


@dataclass
class JobResult:
    jobname: str = field(
        metadata={
            "name": "Job Name",
            "description": "Name of the job configuration",
        }
    )
    groupid: int = field(
        metadata={
            "name": "Thread Group ID",
            "description": (
                "Identifying number for thread group used in a job."
            ),
        }
    )
    error: int = field(
        metadata={
            "name": "Error",
            "description": "An error code thrown by the job.",
        }
    )
    eta: int = field(
        metadata={
            "name": "ETA",
            "description": (
                "Specifies when real-time estimates should be printed."
            ),
        }
    )
    elapsed: int = field(
        metadata={
            "name": "Time Elapsed s",
            "description": "Execution time up to now in seconds.",
        }
    )
    job_options: Dict[str, str] = field(
        metadata={
            "id": "job options",
            "name": "Job Options",
            "description": "Options passed to the fio executable.",
        }
    )
    read: AioOutput = field(
        metadata={
            "name": "Read",
            "description": "Read IO results.",
        }
    )
    write: AioOutput = field(
        metadata={
            "name": "Write",
            "description": "Write IO results.",
        }
    )
    trim: AioOutput = field(
        metadata={
            "name": "Trim",
            "description": "Trim IO results.",
        }
    )
    sync: SyncIoOutput = field(
        metadata={
            "name": "Synchronous",
            "description": "Synchronous IO results.",
        }
    )
    job_runtime: int = field(
        metadata={
            "name": "Runtime",
            "description": "Execution time used on this job.",
        }
    )
    usr_cpu: float = field(
        metadata={
            "name": "User CPU",
            "description": "CPU usage in user space.",
        }
    )
    sys_cpu: float = field(
        metadata={
            "name": "System CPU",
            "description": "CPU usage in kernel (system) space.",
        }
    )
    ctx: int = field(
        metadata={
            "name": "Context Switches",
            "description": (
                "Quantity of voluntary and involuntary context switches."
            ),
        }
    )
    majf: int = field(
        metadata={
            "name": "Major Page Fault",
            "description": "Quantity of page faults requring physical IO.",
        }
    )
    minf: int = field(
        metadata={
            "name": "Minor Page Fault",
            "description": (
                "Quantity of page faults not requiring physical IO."
            ),
        }
    )
    iodepth_level: Dict[str, float] = field(
        metadata={
            "name": "Total IO Depth Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    iodepth_submit: Dict[str, float] = field(
        metadata={
            "name": "Submission IO Depth Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    iodepth_complete: Dict[str, float] = field(
        metadata={
            "name": "Completed IO Depth Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    latency_ns: Dict[str, float] = field(
        metadata={
            "name": "Nanosecond Latency Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    latency_us: Dict[str, float] = field(
        metadata={
            "name": "Microsecond Latency Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    latency_ms: Dict[str, float] = field(
        metadata={
            "name": "Millisecond Latency Frequency Distribution",
            "description": "Unclear from documentation.",
        }
    )
    latency_depth: int = field(
        metadata={
            "name": "Latency Depth",
            "description": "Latency queue depth.",
        }
    )
    latency_target: int = field(
        metadata={
            "name": "Latency Target microseconds",
            "description": "Maximum allowed latency.",
        }
    )
    latency_percentile: float = field(
        metadata={
            "name": "Percent Beat Target Latency",
            "description": "Proportion of IOs that beat the target latency.",
        }
    )
    latency_window: int = field(
        metadata={
            "name": "Latency Window microseconds",
            "description": (
                """Used with Latency Target to specify the sample window"""
                """that the job is run at varying queue depths to test """
                """performance."""
            ),
        }
    )


@dataclass
class DiskUtilization:
    name: str = field(
        metadata={
            "name": "Device Name",
            "description": "Name of the storage device.",
        }
    )
    read_ios: int = field(
        metadata={
            "name": "Read IOs",
            "description": "Quantity of read IO operations.",
        }
    )
    write_ios: int = field(
        metadata={
            "name": "Write IOs",
            "description": "Quantity of write IO operations.",
        }
    )
    read_merges: int = field(
        metadata={
            "name": "Read Merges",
            "description": (
                "Quantity of read merges performed by IO scheduler."
            ),
        }
    )
    write_merges: int = field(
        metadata={
            "name": "Write Merges",
            "description": (
                "Quantity of write merges performed by IO scheduler."
            ),
        }
    )
    read_ticks: int = field(
        metadata={
            "name": "Read Ticks",
            "description": "Quantity of read ticks that kept the device busy.",
        }
    )
    write_ticks: int = field(
        metadata={
            "name": "Write Ticks",
            "description": (
                "Quantity of write ticks that kept the device busy."
            ),
        }
    )
    in_queue: int = field(
        metadata={
            "name": "Time in Queue",
            "description": (
                "Total time spent in device queue. No units are specified in"
                " source, nor documentation."
            ),
        }
    )
    util: float = field(
        metadata={
            "name": "Device Utilization",
            "description": "Proportion of time the device was busy.",
        }
    )
    aggr_read_ios: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Read IOs",
            "description": "Total read IO operations across all workers.",
        },
    )
    aggr_write_ios: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Write IOs",
            "description": "Total write IO operations across all workers.",
        },
    )
    aggr_read_merges: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Read Merges",
            "description": "Total read merges across all workers.",
        },
    )
    aggr_write_merge: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Write Merges",
            "description": "Total write merges across all workers.",
        },
    )
    aggr_read_ticks: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Read Ticks",
            "description": "Total read ticks across all workers.",
        },
    )
    aggr_write_ticks: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Write Ticks",
            "description": "Total write ticks across all workers.",
        },
    )
    aggr_in_queue: Optional[int] = field(
        default=None,
        metadata={
            "name": "Workers' Time in Queue",
            "description": "Total time in queue across all workers.",
        },
    )
    aggr_util: Optional[float] = field(
        default=None,
        metadata={
            "name": "Workers' Device Utilization",
            "description": "Mean device utilization across all workers.",
        },
    )


@dataclass
class FioErrorOutput:
    error: str = field(
        metadata={
            "name": "Job Error Traceback",
            "description": "Fio job traceback for debugging",
        }
    )


@dataclass
class FioSuccessOutput:
    fio_version: str = field(
        metadata={
            "id": "fio version",
            "name": "Fio version",
            "description": "Fio version used on job",
        }
    )
    timestamp: int = field(
        metadata={
            "name": "Timestamp",
            "description": "POSIX compliant timestamp in seconds",
        }
    )
    timestamp_ms: int = field(
        metadata={
            "name": "timestamp ms",
            "description": "POSIX compliant timestamp in milliseconds",
        }
    )
    time: str = field(
        metadata={
            "name": "Time",
            "description": "Human readable datetime string",
        }
    )
    jobs: typing.List[JobResult] = field(
        metadata={
            "name": "Jobs",
            "description": "List of job input parameter configurations",
        }
    )
    global_options: Optional[Dict[str, str]] = field(
        default=None,
        metadata={
            "id": "global options",
            "name": "global options",
            "description": "Options applied to every job",
        },
    )
    disk_util: Optional[typing.List[DiskUtilization]] = field(
        default=None,
        metadata={
            "name": "Disk Utlization",
            "description": "Disk utilization during job",
        },
    )


fio_input_schema = plugin.build_object_schema(FioInput)
job_schema = plugin.build_object_schema(JobResult)
fio_output_schema = plugin.build_object_schema(FioSuccessOutput)
