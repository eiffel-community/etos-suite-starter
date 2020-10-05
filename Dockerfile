FROM python:3.8.3-buster AS build

COPY . /src
WORKDIR /src
RUN python3 setup.py bdist_wheel

FROM python:3.8.3-slim-buster

COPY --from=build /src/dist/*.whl /tmp
# hadolint ignore=DL3013
RUN pip install --no-cache-dir /tmp/*.whl

RUN groupadd -r etos && useradd -r -s /bin/false -g etos etos
USER etos

# DOCKER_CONTEXT is used by ETOS Library to determine whether or not the tool is running in Kubernetes
ENV DOCKER_CONTEXT="ETOS Suite Starter"

LABEL org.opencontainers.image.source=https://github.com/eiffel-community/etos-suite-starter
LABEL org.opencontainers.image.authors=etos-maintainers@googlegroups.com
LABEL org.opencontainers.image.licenses=Apache-2.0

CMD ["python", "-u", "-m", "suite_starter.suite_starter"]
