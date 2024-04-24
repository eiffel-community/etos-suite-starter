==================
ETOS Suite Starter
==================

.. image:: https://img.shields.io/badge/Stage-Sandbox-yellow.svg
  :target: https://github.com/eiffel-community/community/blob/master/PROJECT_LIFECYCLE.md#stage-sandbox

ETOS (Eiffel Test Orchestration System) Suite Starter


Description
===========

The ETOS Suite Starter exist solely to make sure that the ETOS system can be upgrade without any downtime.
It listens to EiffelTestExecutionRecipeCollectionCreatedEvent and launches an instance of ETOS Suite runner in Kubernetes as a Job.


Suite runner configuration
==========================

The Suite runner can be configured using the suite-runner-template configmap. This configmap shall contain a JobTemplate spec where it is possible to provide variables using '{NAME}' where 'NAME' needs to be a variable that the suite starter can access in some way.
Caveat: if you need to have a parameter set to '{}' in the suite runner template, for instance `emptyDir: {}`, then you need to escape the curly braces in a way python can handle: `emptyDir: {{}}` and it will be correct.

.. list-table:: Base deployment
   :widths: 25 25 50
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - EiffelTestExecutionRecipeCollectionCreatedEvent
     - The event that triggered ETOS.
     - The full event. Don't override this
   * - docker_image
     - The suite runner docker image to use
     - Taken from the SUITE_RUNNER environment variable
   * - log_listener
     - The log listener docker image to use
     - Taken from the LOG_LISTENER environment variable
   * - etos_configmap
     - A configmap with environment variables for ETOS.
     - Taken from the ETOS_CONFIGMAP environment variable
   * - etos_rabbitmq_secret
     - A secret with environment variables for ETOS to connect to RabbitMQ
     - Taken from the ETOS_RABBITMQ_SECRET environment variable
   * - ttl
     - Time to live for the suite runner Job
     - ETOS_ESR_TTL or 3600
   * - terminationGracePeriod
     - How long to wait before sending SIGKILL to the suite runner job
     - ETOS_TERMINATION_GRACE_PERIOD or 300
   * - suite_id
     - The event ID of the TERCC event
     - Taken from the TERCC event
   * - job_name
     - The name of the job
     - suite-runner-{suite_id}.lower()

.. list-table:: Filebeat deployment (includes all from Base deployment)
   :widths: 25 25 50
   :header-rows: 1

   * - Name
     - Description
     - Default
   * - sidecar_image
     - The image to use for the filebeat sidecar
     - Taken from the ETOS_SIDECAR_IMAGE environment variable

Installation
============

   pip install .


Contribute
==========

- Issue Tracker: https://github.com/eiffel-community/etos/issues
- Source Code: https://github.com/eiffel-community/etos-suite-starter


Support
=======

If you are having issues, please let us know.
There is a mailing list at: etos-maintainers@googlegroups.com or just write an Issue.
