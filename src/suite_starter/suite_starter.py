#!/usr/bin/env python
# Copyright 2020-2023 Axis Communications AB.
#
# For a full list of individual contributors, please see the commit history.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# -*- coding: utf-8 -*-
"""ETOS suite starter module."""
import json
import logging
import os
from pathlib import Path

from opentelemetry import trace, context
from opentelemetry.propagate import inject

from etos_lib import ETOS
from etos_lib.kubernetes.jobs import Job
from etos_lib.logging.logger import FORMAT_CONFIG
from etos_lib.opentelemetry.semconv import Attributes as SemConvAttributes


LOGGER = logging.getLogger(__name__)
# Remove spam from pika.
logging.getLogger("pika").setLevel(logging.WARNING)


class SuiteStarter:  # pylint:disable=too-many-instance-attributes
    """Suite starter main program."""

    announcement = None

    def __init__(self, suite_runner_template_path: str = "/app/suite_runner_template.yaml"):
        """Initialize SuiteStarter by creating a rabbitmq publisher and subscriber.

        By default the suite starter deployment will mount the suite runner template in
        /app/suite_runner_template.yaml.
        """
        self.etos = ETOS("ETOS Suite Starter", os.getenv("HOSTNAME"), "ETOS Suite Starter")

        self.suite_runner_template = self._load_template(suite_runner_template_path)
        self._configure()
        self._validate_template(self.suite_runner_template)

        self.etos.config.rabbitmq_subscriber_from_environment()
        self.etos.config.rabbitmq_publisher_from_environment()
        self.etos.start_subscriber()
        self.etos.start_publisher()

        self.etos.subscriber.subscribe(
            "EiffelTestExecutionRecipeCollectionCreatedEvent",
            self.suite_runner_callback,
            can_nack=True,
        )
        self.tracer = trace.get_tracer(__name__)

    def _load_template(self, suite_runner_template_path: str) -> str:
        """Load the suite runner template file."""
        suite_runner_template = Path(suite_runner_template_path)
        assert suite_runner_template.is_file(), "Suite runner template is not a file"
        assert suite_runner_template.exists(), "Suite runner template does not exist"
        return suite_runner_template.read_text(encoding="utf-8")

    def _validate_template(self, suite_runner_template: str):
        """Validate that the suite runner template can be deployed."""
        data = {
            "EiffelTestExecutionRecipeCollectionCreatedEvent": "FakeEvent",
            "suite_id": "FakeID",
            "job_name": "FakeName",
            "otel_context": "",
        }
        formatted = suite_runner_template.format(**data, **self.etos.config.get("configuration"))
        job = Job(in_cluster=bool(os.getenv("DOCKER_CONTEXT")))
        job.load_yaml(formatted)

    def _configure(self):
        """Configure ETOS library."""
        configuration = {
            "docker_image": os.getenv("SUITE_RUNNER"),
            "log_listener": os.getenv("LOG_LISTENER"),
            "etos_configmap": os.getenv("ETOS_CONFIGMAP"),
            "etos_observability_configmap": os.getenv("ETOS_OBSERVABILITY_CONFIGMAP"),
            "etos_rabbitmq_secret": os.getenv("ETOS_RABBITMQ_SECRET"),
            "ttl": os.getenv("ETOS_ESR_TTL", "3600"),
            "termination_grace_period": os.getenv("ETOS_TERMINATION_GRACE_PERIOD", "300"),
            "sidecar_image": os.getenv("ETOS_SIDECAR_IMAGE"),
            "otel_exporter_otlp_endpoint": os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or "null",
        }
        self.etos.config.set("configuration", configuration)

    def _get_current_context(self):
        """Get current OpenTelemetry context."""
        ctx = context.get_current()
        LOGGER.info("Current OpenTelemetry context: %s", ctx)
        carrier = {}
        # inject() creates a dict with context reference,
        # e. g. {'traceparent': '00-0be6c260d9cbe9772298eaf19cb90a5b-371353ee8fbd3ced-01'}
        inject(carrier)
        env = ",".join(f"{k}={v}" for k, v in carrier.items())
        return env

    @classmethod
    def remove_empty_configmaps(cls, data):
        """Iterate the ESR configuration dict recursively and remove empty configmaps."""
        element_to_remove = {"configMapRef": {"name": "None"}}
        if isinstance(data, dict):
            for key, value in list(data.items()):
                if value == element_to_remove:
                    del data[key]
                else:
                    cls.remove_empty_configmaps(value)
        elif isinstance(data, list):
            while element_to_remove in data:
                data.remove(element_to_remove)
            for item in data:
                cls.remove_empty_configmaps(item)

    def suite_runner_callback(self, event, _):
        """Start a suite runner on a TERCC event.

        :param event: EiffelTestExecutionRecipeCollectionCreatedEvent (TERCC)
        :type event: :obj: `eiffellib.events.base_event.EiffelTestExecutionRecipeCollectionCreatedEvent`  # noqa pylint:disable=line-too-long
        :return: Whether event was ACK:ed or not.
        :rtype: bool
        """
        with self.tracer.start_as_current_span("suite", context=context.get_current()) as span:
            suite_id = event.meta.event_id
            FORMAT_CONFIG.identifier = suite_id
            LOGGER.info("Received a TERCC event. Build data for ESR.")
            data = {"EiffelTestExecutionRecipeCollectionCreatedEvent": json.dumps(event.json)}
            data["suite_id"] = suite_id
            data["otel_context"] = self._get_current_context()
            span.set_attribute(SemConvAttributes.SUITE_ID, suite_id)

            job = Job(in_cluster=bool(os.getenv("DOCKER_CONTEXT")))
            job_name = job.uniqueify(f"suite-runner-{suite_id}").lower()
            span.set_attribute(SemConvAttributes.SUITE_RUNNER_JOB_ID, job_name)
            data["job_name"] = job_name

            LOGGER.info("Dynamic data: %r", data)
            LOGGER.info("Static data: %r", self.etos.config.get("configuration"))
            try:
                assert data["EiffelTestExecutionRecipeCollectionCreatedEvent"]
            except AssertionError as exception:
                LOGGER.critical("Incomplete data for ESR. %r", exception)
                span.record_exception(exception)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise

            body = job.load_yaml(
                self.suite_runner_template.format(**data, **self.etos.config.get("configuration"))
            )
            # Handle cases when some configmaps aren't set (e. g. etos_observability_configmap):
            self.remove_empty_configmaps(body)

            LOGGER.info("Starting new executor: %r", job_name)
            job.create_job(body)
            LOGGER.info("ESR successfully launched.")
            return True

    def run(self):
        """Run the SuiteStarter main loop.

        Checks if required data has been received within the same context
        and if it does, trigger a runner job within a thread.
        The thread is never joined and is daemonized. This means that if SuiteStarter
        would exit, all tests running within will also exit.
        """
        body = (
            "Suite starter is running and listening to "
            "events in the Eiffel context.\n"
            "Configmap:\n"
            f"ETOS Suite Runner: {os.getenv('SUITE_RUNNER')}\n"
        )
        self.etos.monitor.keep_alive(body)  # Blocking.


def main():
    """Entry point allowing external calls."""
    suite_starter = SuiteStarter()
    suite_starter.run()


def run():
    """Entry point for console_scripts."""
    main()


if __name__ == "__main__":
    run()
