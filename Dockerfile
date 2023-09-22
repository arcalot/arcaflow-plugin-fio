# Package path for this plugin module relative to the repo root
ARG package=arcaflow_plugin_fio

# STAGE 1 -- Build module dependencies and run tests
# The 'poetry' and 'coverage' modules are installed and verson-controlled in the
# quay.io/arcalot/arcaflow-plugin-baseimage-python-buildbase image to limit drift
FROM quay.io/arcalot/arcaflow-plugin-baseimage-python-buildbase:0.3.1@sha256:9767207e2de6597c4d6bd2345d137ac03661326734d4e6824840d270d3415e12 as build
RUN dnf -y install fio-3.19-3.el8
ARG package

COPY poetry.lock /app/
COPY pyproject.toml /app/

# Convert the dependencies from poetry to a static requirements.txt file
RUN python -m poetry install --without dev --no-root \
 && python -m poetry export -f requirements.txt --output requirements.txt --without-hashes

COPY ${package}/ /app/${package}
COPY tests /app/${package}/tests
COPY fixtures /app/fixtures

ENV PYTHONPATH /app/${package}
WORKDIR /app/${package}

# Run tests and return coverage analysis
RUN python -m coverage run tests/test_${package}.py \
 && python -m coverage html -d /htmlcov --omit=/usr/local/*


# STAGE 2 -- Build final plugin image
FROM quay.io/arcalot/arcaflow-plugin-baseimage-python-osbase:0.3.1@sha256:0e9384416ad5dd8810c410a87c283ca29a368fc85592378b85261fce5f9ecbeb
RUN dnf -y install fio-3.19-3.el8
ARG package

COPY --from=build /app/requirements.txt /app/
COPY --from=build /htmlcov /htmlcov/
COPY LICENSE /app/
COPY README.md /app/
COPY ${package}/ /app/${package}

# Install all plugin dependencies from the generated requirements.txt file
RUN python -m pip install -r requirements.txt

WORKDIR /app/${package}

ENTRYPOINT ["python", "fio_plugin.py"]
CMD []


LABEL org.opencontainers.image.source="https://github.com/arcalot/arcaflow-plugin-fio"
LABEL org.opencontainers.image.licenses="Apache-2.0+GPL-2.0-only"
LABEL org.opencontainers.image.vendor="Arcalot project"
LABEL org.opencontainers.image.authors="Arcalot contributors"
LABEL org.opencontainers.image.title="Fio Arcalot Plugin"
LABEL io.github.arcalot.arcaflow.plugin.version="0.1.1"
