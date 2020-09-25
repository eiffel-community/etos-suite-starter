# Copyright 2020 Axis Communications AB.
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
"""YAML for launching ETOS Suite Runner in Kubernetes."""

ESR_YAML = (
    "apiVersion: batch/v1\n"
    "kind: Job\n"
    "metadata:\n"
    "  name: {job_name}\n"
    "  labels:\n"
    "    app: suite-runner\n"
    "    id: {suite_id}\n"
    "spec:\n"
    "  template:\n"
    "    metadata:\n"
    "      name: {job_name}\n"
    "    spec:\n"
    "      serviceAccountName: etos-sa\n"
    "      containers:\n"
    "      - name: {job_name}\n"
    "        image: {docker_image}\n"
    "        imagePullPolicy: Always\n"
    "        envFrom:\n"
    "        - configMapRef:\n"
    "            name: {etos_configmap}\n"
    "        env:\n"
    "        - name: TERCC\n"
    "          value: '{EiffelTestExecutionRecipeCollectionCreatedEvent}'\n"
    "        - name: RABBITMQ_PASSWORD\n"
    "          valueFrom:\n"
    "            secretKeyRef:\n"
    "              name: rabbitmq\n"
    "              key: password\n"
    "        - name: RABBITMQ_USERNAME\n"
    "          valueFrom:\n"
    "            secretKeyRef:\n"
    "              name: rabbitmq\n"
    "              key: username\n"
    "      restartPolicy: Never\n"
    "  backoffLimit: 0\n"
)
