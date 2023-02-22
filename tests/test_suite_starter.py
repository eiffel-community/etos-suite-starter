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
"""Test module for ETOS suite starter."""
import os
import uuid
import json
import logging
from unittest import TestCase
from mock import patch

from eiffellib.events import EiffelTestExecutionRecipeCollectionCreatedEvent
from etos_lib.lib.config import Config

from suite_starter.suite_starter import SuiteStarter

# It's okay since it's tests. pylint:disable=broad-exception-raised
LOGGER = logging.getLogger("TESTS")

os.environ["ETOS_DISABLE_SENDING_EVENTS"] = "1"  # True
os.environ["ETOS_DISABLE_RECEIVING_EVENTS"] = "1"  # True


def step(msg):
    """Test step printer."""
    LOGGER.info("STEP: %s", msg)


class TestSuiteStarter(TestCase):
    """Tests for SuiteStarter."""

    etos_configmap = "thisisanothername"
    suite_runner = "ESR"

    def setUp(self):
        os.environ["ETOS_CONFIGMAP"] = self.etos_configmap
        os.environ["SUITE_RUNNER"] = self.suite_runner
        Config().reset()

    def _kubernetes_env_to_dict(self, yaml):
        """Convert kubernetes YAML environment variables to dict.

        :param yaml: YAML dict to convert.
        :type yaml: dict
        :return: Environment variables for this spec.
        :rtype: dict
        """
        environment_dict = {}
        for _, value in self.search(yaml, "env"):
            for variable in value:
                if variable.get("value"):
                    environment_dict[variable["name"]] = variable["value"]
        return environment_dict

    def search(self, dictionary, *keys):
        """Recursively search for keys in a nested dictionary.

        :param dictionary: Dictionary to search in.
        :type dictionary: dict
        :param keys: Keys to search for.
        :type keys: list
        :return: key and value matching the search.
        :rtype: tuple
        """
        for key, value in dictionary.items():
            if key in keys:
                yield key, value
            if isinstance(value, dict):
                for dict_key, dict_value in self.search(value, *keys):
                    yield dict_key, dict_value
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, dict):
                        for dict_key, dict_value in self.search(item, *keys):
                            yield dict_key, dict_value

    @staticmethod
    def _generate_tercc():
        """Generate a test execution recipe collection created event for test.

        :return: TERCC.
        :rtype: :obj:`EiffelTestExecutionRecipeCollectionCreatedEvent`
        """
        tercc = EiffelTestExecutionRecipeCollectionCreatedEvent()
        tercc.data.add("batchesUri", "http://internet.se")
        selection_strategy = {
            "tracker": "Suite Builder",
            "id": str(uuid.uuid4()),
            "uri": "http://tracker.com",
        }
        tercc.data.add("selectionStrategy", selection_strategy)
        tercc.links.add("CAUSE", str(uuid.uuid4()))
        return tercc

    @patch("suite_starter.suite_starter.Job._load_config")
    @patch("suite_starter.suite_starter.Job.create_job")
    def test_suite_starter_tercc(self, mock_job, _):
        """Test that suite starter sends the correct TERCC to ESR.

        Approval criteria:
            - Event ID of TERCC sent from SuiteStarter shall be the same as provided.

        Test steps:
            1. Execute SuiteStarter with TERCC as input.
            2. Check that SuiteStarter executed correctly.
            3. Verify that TERCC sent from SuiteStarter matches the one supplied when executing.
        """
        step("Execute SuiteStarter with TERCC as input.")
        suite_starter = SuiteStarter()
        tercc = self._generate_tercc()
        return_value = suite_starter.suite_runner_callback(tercc, tercc.meta.event_id)
        step("Check that SuiteStarter executed correctly.")
        if not return_value:
            raise Exception("SuiteStarter did not execute properly.")

        yaml = mock_job.call_args[0][0]

        step(
            "Verify that TERCC sent from SuiteStarter matches the one supplied when executing."
        )
        environment_dict = self._kubernetes_env_to_dict(yaml)
        self.assertEqual(
            json.loads(environment_dict["TERCC"])["meta"]["id"], tercc.meta.event_id
        )

    @patch("suite_starter.suite_starter.Job._load_config")
    @patch("suite_starter.suite_starter.Job.create_job")
    def test_suite_starter_configmaps(self, mock_job, _):
        """Test that suite starter sends the correct TERCC to ESR.

        Approval criteria:
            - SuiteStarter shall attach correct configmaps from environment variables to ESR.

        Test steps:
            1. Execute SuiteStarter with TERCC as input.
            2. Check that SuiteStarter executed correctly.
            3. Verify that configmaps are sent to ESR.
        """
        step("Execute SuiteStarter with TERCC as input.")
        suite_starter = SuiteStarter()
        tercc = self._generate_tercc()
        return_value = suite_starter.suite_runner_callback(tercc, tercc.meta.event_id)
        step("Check that SuiteStarter executed correctly.")
        if not return_value:
            raise Exception("SuiteStarter did not execute properly.")

        yaml = mock_job.call_args[0][0]

        step("Verify that configmaps are sent to ESR.")
        configmaps = [value["name"] for _, value in self.search(yaml, "configMapRef")]
        self.assertIn(
            self.etos_configmap,
            configmaps,
            "ETOS Configmap is not available in kubernetes yaml.",
        )
        self.assertEqual(
            len(configmaps), 1, "There are too many configmaps in kubernetes yaml."
        )

    @patch("suite_starter.suite_starter.Job._load_config")
    @patch("suite_starter.suite_starter.Job.create_job")
    def test_suite_starter_esr_image(self, mock_job, _):
        """Test that suite starter sends the correct DockerImage to ESR.

        Approval criteria:
            - SuiteStarter shall attach correct configmaps from environment variables to ESR.

        Test steps:
            1. Execute SuiteStarter with TERCC as input.
            2. Check that SuiteStarter executed correctly.
            3. Verify that the correct docker image is sent to ESR.
        """
        step("Execute SuiteStarter with TERCC as input.")
        suite_starter = SuiteStarter()
        tercc = self._generate_tercc()
        return_value = suite_starter.suite_runner_callback(tercc, tercc.meta.event_id)
        step("Check that SuiteStarter executed correctly.")
        if not return_value:
            raise Exception("SuiteStarter did not execute properly.")

        yaml = mock_job.call_args[0][0]

        step("Verify that the correct docker image is sent to ESR.")
        image = [value for _, value in self.search(yaml, "image")]
        self.assertEqual(
            len(image),
            1,
            f"There is not exactly 1 docker image in kubernetes yaml. There was: {len(image)}",
        )
        self.assertEqual(
            image[0],
            self.suite_runner,
            "Docker image sent to ESR is not correct. "
            f"Expected {self.suite_runner!r}, Was {image[0]!r}",
        )

    @patch("suite_starter.suite_starter.Job")
    def test_suite_starter_missing_etos_configmap(self, _):
        """Test that suite starter aborts if 'ETOS_CONFIGMAP' is missing from environment.

        Approval criteria:
            - SuiteStarter shall abort execution if ETOS_CONFIGMAP is missing.

        Test steps:
            1. Execute SuiteStarter without ETOS_CONFIGMAP.
            2. Verify that SuiteStarter did not execute correctly.
        """
        del os.environ["ETOS_CONFIGMAP"]
        step("Execute SuiteStarter without ETOS_CONFIGMAP")
        suite_starter = SuiteStarter()
        tercc = self._generate_tercc()

        step("Verify that SuiteStarter did not execute correctly.")
        expected_message = "Missing ETOS_CONFIGMAP in environment"
        with self.assertRaises(AssertionError) as context:
            suite_starter.suite_runner_callback(tercc, tercc.meta.event_id)
        self.assertEqual(
            str(context.exception),
            expected_message,
            "SuiteStarter did not fail with AssertionError on the correct parameter. "
            f"Expected: {expected_message!r}. Was: {context.exception!r}",
        )

    @patch("suite_starter.suite_starter.Job")
    def test_suite_starter_missing_suite_starter_suite_runner(self, _):
        """Test that suite starter aborts if 'SUITE_RUNNER' is missing from environment.

        Approval criteria:
            - SuiteStarter shall abort execution if SUITE_RUNNER is missing.

        Test steps:
            1. Execute SuiteStarter without SUITE_RUNNER.
            2. Verify that SuiteStarter did not execute correctly.
        """
        del os.environ["SUITE_RUNNER"]

        step("Execute SuiteStarter without SUITE_RUNNER")
        suite_starter = SuiteStarter()
        tercc = self._generate_tercc()

        step("Verify that SuiteStarter did not execute correctly.")
        with self.assertRaises(AssertionError) as context:
            suite_starter.suite_runner_callback(tercc, tercc.meta.event_id)
        expected_message = "Missing SUITE_RUNNER in environment"
        self.assertEqual(
            str(context.exception),
            expected_message,
            "SuiteStarter did not fail with AssertionError on the correct parameter. "
            f"Expected: {expected_message!r}. Was: {context.exception!r}",
        )
