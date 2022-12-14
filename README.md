# Arcaflow Plugin Fio

This plugin executes the fio workload software with a given input schema defined in a yaml file.

## Image Building

You can change this plugin's image version tag in
`.github/workflows/carpenter.yaml` by editing the
`IMAGE_TAG` variable, and pushing that change to the
branch designated in that workflow.

## Run the thing

### Containerized

#### Requirements

* fio_plugin image named `fio-plugin`
* current working directory is the fio plugin root

```shell
cat fixtures/poisson-rate-submission_input.yaml | docker run -i fio-plugin -f -
```

### Raw

#### Requirements

* Current working directory is the fio plugin root
* Python virtual environment created based on this project's pyproject.toml, and activated
* [fio](https://fio.readthedocs.io/en/latest/fio_doc.html#binary-packages) installed locally


```shell
python fio_plugin.py -f fixtures/poisson-rate-submission_input.yaml
```

```shell
python test_fio_plugin.py
```

## Terms

[rusage documentation](https://docs.oracle.com/cd/E36784_01/html/E36870/rusage-1b.html) relevant to fio

* `nvcsw` Number of voluntary context switches
* `nivcsw` Number of involuntary context switches
* `minflt` page faults requiring physical IO
* `majflt` page faults not requiring physical IO

