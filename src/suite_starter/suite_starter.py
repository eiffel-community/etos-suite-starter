#!/usr/bin/env python
# Copyright 2020-2021 Axis Communications AB.
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
import os
import logging
import json

from etos_lib import ETOS
from etos_lib.kubernetes.jobs import Job
from etos_lib.logging.logger import FORMAT_CONFIG

from suite_starter.esr_yaml import ESR_YAML, ESR_YAML_WITH_SIDECAR

LOGGER = logging.getLogger(__name__)
# Remove spam from pika.
logging.getLogger("pika").setLevel(logging.WARNING)


class SuiteStarter:  # pylint:disable=too-many-instance-attributes
    """Suite starter main program."""

    announcement = None

    def __init__(self):
        """Initialize SuiteStarter by creating a rabbitmq publisher and subscriber."""
        self.etos = ETOS(
            "ETOS Suite Starter", os.getenv("HOSTNAME"), "ETOS Suite Starter"
        )
        self._configure()

        self.etos.config.rabbitmq_subscriber_from_environment()
        self.etos.config.rabbitmq_publisher_from_environment()
        self.etos.start_subscriber()
        self.etos.start_publisher()

        self.etos.subscriber.subscribe(
            "EiffelTestExecutionRecipeCollectionCreatedEvent",
            self.suite_runner_callback,
            can_nack=True,
        )

    def _configure(self):
        """Configure ETOS library."""
        self.etos.config.set("suite_runner", os.getenv("SUITE_RUNNER"))

    def suite_runner_callback(self, event, _):
        """Start a suite runner on a TERCC event.

        :param event: EiffelTestExecutionRecipeCollectionCreatedEvent (TERCC)
        :type event: :obj: `eiffellib.events.base_event.EiffelTestExecutionRecipeCollectionCreatedEvent`  # noqa pylint:disable=line-too-long
        :return: Whether event was ACK:ed or not.
        :rtype: bool
        """
        suite_id = event.meta.event_id
        FORMAT_CONFIG.identifier = suite_id
        LOGGER.info("Received a TERCC event. Build data for ESR.")
        data = {
            "EiffelTestExecutionRecipeCollectionCreatedEvent": json.dumps(event.json)
        }
        data["etos_configmap"] = os.getenv("ETOS_CONFIGMAP")
        data["docker_image"] = self.etos.config.get("suite_runner")
        data["suite_id"] = suite_id
        with_sidecar = os.getenv("ETOS_SIDECAR_ENABLED", "false").lower() == "true"
        if with_sidecar:
            data["sidecar_image"] = os.getenv("ETOS_SIDECAR_IMAGE")

        job = Job(in_cluster=bool(os.getenv("DOCKER_CONTEXT")))
        job_name = job.uniqueify("suite-runner-{}".format(suite_id)).lower()
        data["job_name"] = job_name

        LOGGER.info("Data: %r", data)
        try:
            assert data["EiffelTestExecutionRecipeCollectionCreatedEvent"]
            assert data["etos_configmap"], "Missing ETOS_CONFIGMAP in environment"
            assert data["docker_image"], "Missing SUITE_RUNNER in environment"
        except AssertionError as exception:
            LOGGER.critical("Incomplete data for ESR. %r", exception)
            raise

        if with_sidecar:
            body = job.load_yaml(ESR_YAML_WITH_SIDECAR.format(**data))
        else:
            body = job.load_yaml(ESR_YAML.format(**data))
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
            "ETOS Suite Runner: {}\n".format(os.getenv("SUITE_RUNNER"))
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
