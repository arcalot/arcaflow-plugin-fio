#!/usr/bin/env python3

import typing
import re
import enum
import configparser
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict
from pathlib import Path

from arcaflow_plugin_sdk import plugin, schema, validation


class KbBase(enum.IntEnum):
    KB = 1000
    KIB = 1024


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


duration_pattern_string = r"[1-9][0-9]*(?:d|h|m|s|ms|us)?"
duration_pattern = re.compile(rf"^{duration_pattern_string}$")
duration_range_pattern = re.compile(
    rf"^{duration_pattern_string}(?:-{duration_pattern_string})?$"
)

size_pattern_string = (
    r"0x[0-9a-fA-F]+|"
    r"\d+(?:k|kb|ki|kib|m|mb|mi|mib|g|gb|gi|gib|t|tb|ti|tib|p|pb|pi|pib)?"
)
size_pattern = re.compile(
    rf"^(?:{size_pattern_string}(?:,{size_pattern_string}){{0,2}})$",
    re.IGNORECASE,
)

size_pattern_with_percent_string = rf"{size_pattern_string}|[1-9][0-9]?%|100%"
size_pattern_with_percent = re.compile(
    rf"^(?:{size_pattern_with_percent_string})$", re.IGNORECASE
)

size_range_pattern_string = (
    rf"(?:{size_pattern_string})-(?:{size_pattern_string})"
)
size_range_pattern = re.compile(
    rf"^{size_range_pattern_string}$",
    re.IGNORECASE,
)

size_multi_range_pattern = re.compile(
    rf"^{size_range_pattern_string}"
    rf"(?:,{size_range_pattern_string}){{0,2}}$",
    re.IGNORECASE,
)


@dataclass
class JobParams:
    # Units
    kb_base: typing.Annotated[
        typing.Optional[KbBase],
        schema.name("Units Base"),
        schema.description(
            "Select the interpretation of unit prefixes in input parameters. The "
            "default is 1024 (compatibility mode): Power-of-2 values with SI prefixes "
            "(e.g., KB) and Power-of-10 values with IEC prefixes (e.g., KiB). When "
            "setting this to 1000, inputs comply with IEC 80000-13 and the "
            "International System of Units (SI): Power-of-2 values with IEC prefixes "
            "(e.g., KiB) and Power-of-10 values with SI prefixes (e.g., KB)"
        ),
    ] = None

    # Job Description
    loops: typing.Annotated[
        typing.Optional[int],
        schema.name("Number of Job Loops"),
        schema.description(
            "Run the specified number of iterations of this job. Used to repeat the "
            "same workload a given number of times. Default is 1."
        ),
    ] = None
    numjobs: typing.Annotated[
        typing.Optional[int],
        schema.name("Number of Job Clones"),
        schema.description(
            "Create the specified number of clones of this job. Each clone of job is "
            "spawned as an independent thread or process. May be used to set up a "
            "larger number of threads/processes doing the same thing. Each thread is "
            "reported separately. Default is 1."
        ),
    ] = None

    # Time related parameters
    runtime: typing.Annotated[
        typing.Optional[str],
        validation.pattern(duration_pattern),
        schema.name("Job Run Time"),
        schema.description(
            "Limit runtime. The test will run until it completes the configured I/O "
            "workload or until it has run for this specified amount of time, whichever "
            "occurs first. When the unit is omitted, the value is interpreted in "
            "seconds. Default behavior is size-based operation."
        ),
    ] = None
    time_based: typing.Annotated[
        typing.Optional[bool],
        schema.name("Time Based"),
        schema.description(
            "If set, fio will run for the duration of the runtime specified even if "
            "the file(s) are completely read or written. It will simply loop over the "
            "same workload as many times as the runtime allows. Default is false."
        ),
    ] = None
    startdelay: typing.Annotated[
        typing.Optional[str],
        validation.pattern(duration_range_pattern),
        schema.name("Job Start Delay"),
        schema.description(
            "Delay the start of job for the specified amount of time. Can be a single "
            "value or a range. When given as a range, each thread will choose a value "
            "randomly from within the range. Value is in seconds if a unit is omitted. "
            "Default is 0."
        ),
    ] = None
    ramp_time: typing.Annotated[
        typing.Optional[str],
        validation.pattern(duration_pattern),
        schema.name("Job Ramp Time"),
        schema.description(
            "Run the specified workload for this amount of time before logging any "
            "performance numbers. Useful for letting performance settle before logging "
            "results, thus minimizing the runtime required for stable results. Note "
            "that the ramp_time is considered lead in time for a job, thus it will "
            "increase the total runtime if a special timeout or runtime is specified. "
            "When the unit is omitted, the value is given in seconds. Default is 0."
        ),
    ] = None

    # Target file/device
    directory: typing.Annotated[
        typing.Optional[str],
        schema.name("Job Directory"),
        schema.description(
            "Prefix filenames with this directory. Used to place files in a different "
            "location than './'. You can specify a number of directories by separating "
            "the names with a ':' character. These directories will be assigned "
            "equally distributed to job clones created by numjobs as long as they are "
            "using generated filenames. If specific filename(s) are set fio will use "
            "the first listed directory, and thereby matching the filename semantic "
            "(which generates a file for each clone if not specified, but lets all "
            "clones use the same file if set). Default is the current directory."
        ),
    ] = None
    filename: typing.Annotated[
        typing.Optional[str],
        schema.name("File Name"),
        schema.description(
            "Fio normally makes up a filename based on the job name, thread number, "
            "and file number. If you want to share files between threads in a job or "
            "several jobs with fixed file paths, specify a filename for each of them "
            "to override the default. If the ioengine is file based, you can specify a "
            "number of files by separating the names with a ':' colon. So if you "
            "wanted a job to open '/dev/sda' and '/dev/sdb' as the two working files, "
            "you would use 'filename=/dev/sda:/dev/sdb'. This also means that whenever "
            "this option is specified, nrfiles is ignored. The size of regular files "
            "specified by this option will be size divided by number of files unless "
            "an explicit size is specified by filesize."
        ),
    ] = None
    nrfiles: typing.Annotated[
        typing.Optional[int],
        validation.min(1),
        schema.name("Number of Files"),
        schema.description(
            "Number of files to use for this job. The size of files will be size "
            "divided by this unless explicit size is specified by filesize. Files are "
            "created for each thread separately, and each file will have a file number "
            "within its name by default, as explained in filename section. Default is "
            "1."
        ),
    ] = None
    openfiles: typing.Annotated[
        typing.Optional[int],
        validation.min(1),
        schema.name("Concurrent Open Files"),
        schema.description(
            "Number of files to keep open at the same time. Defaults to the same as "
            "nrfiles, but can be set smaller to limit the number simultaneous opens."
        ),
    ] = None
    create_on_open: typing.Annotated[
        typing.Optional[bool],
        schema.name("Create Files on Open"),
        schema.description(
            "Don't pre-create files but allow the job's open() to create a file when "
            "it's time to do I/O. Defaults to false."
        ),
    ] = None
    pre_read: typing.Annotated[
        typing.Optional[bool],
        schema.name("Pre-Read Files"),
        schema.description(
            "Files will be pre-read into memory before starting the given I/O "
            "operation. This will also clear the invalidate flag, since it is "
            "pointless to pre-read and then drop the cache. This will only work for "
            "I/O engines that are seek-able, since they allow you to read the same "
            "data multiple times. Thus it will not work on non-seekable I/O engines "
            "(e.g. network, splice). Defaults to false."
        ),
    ] = None
    unlink: typing.Annotated[
        typing.Optional[bool],
        schema.name("Unlink Files"),
        schema.description(
            "Unlink the job files when done. Not the default, as repeated runs of that "
            "job would then waste time recreating the file set again and again. "
            "Defaults to false."
        ),
    ] = None
    unlink_each_loop: typing.Annotated[
        typing.Optional[bool],
        schema.name("Unlink Files Each Loop"),
        schema.description(
            "Unlink job files after each iteration or loop. Defaults to False."
        ),
    ] = None

    # I/O Type
    direct: typing.Annotated[
        typing.Optional[bool],
        schema.name("Direct I/O"),
        schema.description(
            "Use non-buffered I/O. This is usually O_DIRECT. Note that OpenBSD and ZFS "
            "on Solaris don't support direct I/O. On Windows the synchronous ioengines "
            "don't support direct I/O. This is the opposite of the buffered option and "
            "defaults to False."
        ),
    ] = None
    buffered: typing.Annotated[
        Optional[bool],
        schema.name("Buffered"),
        schema.description(
            "Use buffered I/O. This is the opposite of the direct option and defaults "
            "to True."
        ),
    ] = None
    readwrite: typing.Annotated[
        typing.Optional[IoPattern],
        schema.name("Read/Write"),
        schema.description(
            "Type of IO pattern. Defaults to read. For the mixed I/O types, the "
            "default is to split them 50/50. For certain types of I/O the result may "
            "still be skewed a bit since the speed may be different."
        ),
    ] = None

    # Block size
    blocksize: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_pattern),
        schema.name("Block Size"),
        schema.description(
            "Block size in bytes used for I/O units. A single value applies to reads, "
            "writes, and trims. Comma-separated values may be specified for reads, "
            "writes, and trims. A value not terminated in a comma applies to "
            "subsequent types. Defaults to 4096."
        ),
    ] = None
    blocksize_range: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_multi_range_pattern),
        schema.name("Block Size Range"),
        schema.description(
            "A range of block sizes in bytes for I/O units. The issued I/O unit will "
            "always be a multiple of the minimum size, unless blocksize_unaligned is "
            "set. Comma-separated ranges may be specified for reads, writes, and trims "
            "as described in blocksize. A range is not used by default."
        ),
    ] = None

    # I/O  size
    size: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_pattern_with_percent),
        schema.name("Total I/O Size"),
        schema.description(
            "The total size of file I/O for each thread of this job. Fio will run "
            "until this many bytes have been transferred, unless runtime is altered by "
            "other means such as (1) runtime, (2) io_size, (3) number_ios, (4) "
            "gaps/holes while doing I/O's such as 'rw=read:16K', or (5) sequential "
            "I/O reaching end of the file which is possible when percentage_random is "
            "less than 100. Fio will divide this size between the available files "
            "determined by options such as nrfiles or filename, unless filesize is "
            "specified by the job. If the result of division happens to be 0, the size "
            "is set to the physical size of the given files or devices if they exist. "
            "If this option is not specified, fio will use the full size of the given "
            "files or devices. If the files do not exist, size must be given. It is "
            "also  possible to give size as a percentage between 1 and 100. If "
            "'size=20%' is given, fio will use 20% of the full size of the given files "
            "or devices."
        ),
    ] = None
    io_size: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_pattern_with_percent),
        schema.name("I/O Size"),
        schema.description(
            "Normally fio operates within the region set by size, which means that the "
            "size option sets both the region and size of I/O to be performed. "
            "Sometimes that is not what you want. With this option, it is possible to "
            "define just the amount of I/O that fio should do. For instance, if size "
            "is set to 20GiB and io_size is set to 5GiB, fio will perform I/O within "
            "the first 20GiB but exit when 5GiB have been done. The opposite is also "
            "possible -- if size is set to 20GiB, and io_size is set to 40GiB, then "
            "fio will do 40GiB of I/O within the 0..20GiB region. Value can be set as "
            "percentage: io_size=N%. In this case io_size multiplies size= value."
        ),
    ] = None
    filesize: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_range_pattern),
        schema.name("File Size"),
        schema.description(
            "Individual file sizes. May be a range, in which case fio will select "
            "sizes for files at random within the given range. If not given, each "
            "created file is the same size. This option overrides size in terms of "
            "file size, i.e. size becomes merely the default for io_size (and has no "
            "effect at all if io_size is set explicitly)."
        ),
    ] = None

    # I/O engine
    ioengine: typing.Annotated[
        typing.Optional[IoEngine],
        schema.name("IO Engine"),
        schema.description(
            "Defines how the job issues I/O to the file. Default is sync."
        ),
    ] = None

    # I/O depth
    iodepth: typing.Annotated[
        typing.Optional[int],
        validation.min(1),
        schema.name("IO Depth"),
        schema.description(
            "Number of I/O units to keep in flight against the file. Note that "
            "increasing iodepth beyond 1 will not affect synchronous ioengines (except "
            "for small degrees when verify_async is in use). Even async engines may "
            "impose OS restrictions causing the desired depth not to be achieved. This "
            "may happen on Linux when using libaio and not setting 'direct=1', since "
            "buffered I/O is not async on that OS. Keep an eye on the I/O depth "
            "distribution in the fio output to verify that the achieved depth is as "
            "expected. Default is 1."
        ),
    ] = None
    io_submit_mode: typing.Annotated[
        typing.Optional[IoSubmitMode],
        schema.name("IO Submit Mode"),
        schema.description(
            "Controls how fio submits the I/O to the I/O engine. The default is "
            "'inline', which  means that the fio job threads submit and reap I/O "
            "directly. If set to 'offload', the job threads will offload I/O "
            "submission to a dedicated pool of I/O threads. This requires some "
            "coordination and thus has a bit of extra overhead, especially for lower "
            "queue depth I/O where it can increase latencies. The benefit is that fio "
            "can manage submission rates independently of the device completion rates. "
            "This avoids skewed latency reporting if I/O gets backed up on the device "
            "side (the coordinated omission problem). Note that this option cannot "
            "reliably be used with async IO engines."
        ),
    ] = None

    # I/O rate
    rate_iops: typing.Annotated[
        typing.Optional[str],
        validation.pattern(size_pattern),
        schema.name("IOPS Cap"),
        schema.description(
            "Cap the bandwidth to this number of IOPS. Basically the same as rate, "
            "just specified independently of bandwidth. If the job is given a block "
            "size range instead of a fixed value, the smallest block size is used as "
            "the metric. Comma-separated values may be specified for reads, writes, "
            "and trims as described in blocksize."
        ),
    ] = None
    rate_process: typing.Annotated[
        typing.Optional[RateProcess],
        schema.name("Rate Process"),
        schema.description(
            "Controls how fio manages rated I/O submissions. The default is 'linear', "
            "which submits I/O in a linear fashion with fixed delays between I/Os that "
            "gets adjusted based on I/O completion rates. If this is set to 'poisson', "
            "fio will submit I/O based on a more real world random request flow, known "
            "as the Poisson process "
            "(https://en.wikipedia.org/wiki/Poisson_point_process). The lambda will be "
            "10^6 / IOPS for the given workload."
        ),
    ] = None

    # Threads, processes, and job synchronization
    stonewall: typing.Annotated[
        typing.Optional[bool],
        schema.name("Stonewall"),
        schema.description(
            "Wait for preceding jobs in the job file to exit, before starting this "
            "one. Can be used to insert serialization points in the job file. A "
            "stonewall also implies starting a new reporting group, (see "
            "group_reporting). Default is false."
        ),
    ] = None


@dataclass
class FioJob:
    name: typing.Annotated[
        str,
        schema.name("Job Name"),
        schema.description("User-defined ASCII name of the job."),
    ]
    params: typing.Annotated[
        JobParams,
        schema.name("Fio Job Parameters"),
        schema.description("Parameters for the fio job."),
    ]


@dataclass
class FioInput:
    jobs: typing.Annotated[
        typing.List[FioJob],
        schema.name("Fio Jobs List"),
        schema.description("List of jobs for fio to run."),
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
                    if isinstance(value, (bool, int)):
                        item_value = str(int(value))
                    else:
                        item_value = str(value)
                    cfg[job.name][key] = str(item_value)
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
