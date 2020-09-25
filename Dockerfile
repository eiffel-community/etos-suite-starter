FROM python:3.8.3

# DOCKER_CONTEXT is used by ETOS Library to determine whether or not the tool is running in Kubernetes
ENV DOCKER_CONTEXT="ETOS Suite Starter"
ARG PIP_ARGS

RUN useradd -ms /bin/bash etos
USER etos

ENV PATH="/home/etos/.local/bin:${PATH}"

RUN pip install $PIP_ARGS --upgrade pip
WORKDIR /usr/src/app/src
CMD ["python", "-u", "-m", "suite_starter.suite_starter"]

COPY requirements.txt /requirements.txt
RUN pip install $PIP_ARGS -r /requirements.txt

COPY . /usr/src/app
