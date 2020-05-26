"""
This script reads pipeline name as an input, reads config  and launches the pipeline accordingly

Job Monitoring url -> https://console.cloud.google.com/dataflow/jobsDetail/locations/%s/jobs/%s?project=%s


 https://cloud.google.com/dataflow/docs/reference/rest
 https://cloud.google.com/dataflow/docs/guides/templates/running-templates#example-1:-creating-a-custom-template-batch-job
 https://cloud.google.com/dataflow/docs/guides/templates/using-flex-templates#running_a_flex_template_pipeline

Traditional Templates -> https://dataflow.googleapis.com/v1b3/projects/YOUR_PROJECT_ID/templates:launch?gcsPath=gs://YOUR_BUCKET_NAME/templates/TemplateName
Flex Templates -> https://dataflow.googleapis.com/v1b3/projects/$PROJECT/locations/us-central1/flexTemplates:launch
"""
import argparse
import logging
import re
import select
import subprocess
#import sys
import time
from collections import namedtuple
from copy import deepcopy
from datetime import datetime, timedelta
from enum import Enum, unique
from typing import Callable, Dict, List, Optional

import google.auth
from googleapiclient.discovery import build

import AppExceptions
import pipelineconfig

#TODO: retry capability
JOB_ID_PATTERN = re.compile(r"https?://console\.cloud\.google\.com/dataflow.*/jobs/(.+)\?")

SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


POLLINTERVAL_IN_SECONDS = 60  #1 Amount of time to sleep while checking for the comletion of the job
TIMEOUT_IN_SECONDS = 30 * 60  #5 Amount of time before giving up monitoring job status
NUM_OF_RETRIES = 5
PIPELINE_RUNNER = "DataflowRunner" # DataflowRunner DirectRunner


class DataflowJobStates(object):
    """Helper class with Dataflow job states
    Refer https://cloud.google.com/dataflow/docs/reference/rest/v1b3/projects.jobs#jobstate
    """
    JOB_STATE_PENDING = "JOB_STATE_PENDING"
    JOB_STATE_RUNNING = "JOB_STATE_RUNNING"
    JOB_STATE_DONE = "JOB_STATE_DONE"
    JOB_STATE_FAILED = "JOB_STATE_FAILED"
    JOB_STATE_CANCELLED = "JOB_STATE_CANCELLED"
    JOB_STATE_STOPPED = "JOB_STATE_STOPPED"
    JOB_STATE_DRAINED = "JOB_STATE_DRAINED"
    JOB_STATE_UPDATED = "JOB_STATE_UPDATED"
    JOB_STATE_UNKNOWN = "JOB_STATE_UNKNOWN"
    INTERRUPTED_STATES = {
        JOB_STATE_STOPPED, JOB_STATE_CANCELLED, JOB_STATE_DRAINED,
        JOB_STATE_UPDATED
    }
    #SUCCEEDED_END_STATES = {JOB_STATE_DONE}
    COMPLETE_STATES = {JOB_STATE_DONE, JOB_STATE_FAILED}
    END_STATES = {JOB_STATE_DONE, JOB_STATE_FAILED, JOB_STATE_UNKNOWN
                 } | INTERRUPTED_STATES

def parse_cliargs() -> argparse.Namespace:
    """Parse command line args"""
    args_parser = argparse.ArgumentParser(description='Dataflow Job  Launcher')

    args_parser.add_argument('--pipelinename',
                             type=str,
                             choices=pipelineconfig.pipelines.keys(),
                             help="Pipeline name",
                             required=True)

    args_parser.add_argument('--language',
                             type=str,
                             choices=["java", "python"],
                             help="Pipeline name",
                             default="python",
                             required=False)
    return args_parser.parse_args()


def read_line_by_fd(_proc, fd):
    """Read line by line from the file descriptors"""
    if fd == _proc.stderr.fileno():
        line = _proc.stderr.readline().decode()
        if line:
            logging.info(line.strip())  # just to remove trailing slash [:-1]
        return line

    if fd == _proc.stdout.fileno():
        line = _proc.stdout.readline().decode()
        if line:
            logging.info(line.strip())  # just to remove trailing slash
        return line

    raise Exception("No data in stderr or in stdout.")


def _extract_job(line: str) -> Optional[str]:
    """Extracts job_id based on the expected pattern"""
    matched_job = JOB_ID_PATTERN.search(line)
    if matched_job:
        job_id = matched_job.group(1).split("/")[-1]
        return job_id
    return None


def _start_dfjob(job_name: str, workingdir: str, command: List[str]) -> str:
    """Start dataflow job and return Job id"""

    logging.info("Running command %s in directory %s", " ".join(command),
                 workingdir)
    #return "2020-05-13_09_24_15-17707944884287612376"
    try:
        _proc = subprocess.Popen(command,
                                 shell=False,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 close_fds=True,
                                 cwd=workingdir)

        reads = [
            _proc.stderr.fileno() if _proc.stderr else 0,
            _proc.stdout.fileno() if _proc.stdout else 0
        ]
        returncode = None
        job_id = None
        error_lines = None
        while returncode is None and job_id is None:
            # Wait for at least one available fd.
            readable_fds, _, _ = select.select(reads, [], [],
                                               5)  # Times out in 5 seconds
            if readable_fds is None:
                print("Waiting for external process to start.")
                continue

            # Read available fds.
            for readable_fd in readable_fds:
                line = read_line_by_fd(_proc, readable_fd)
                if line:
                    job_id = _extract_job(line)

            returncode = _proc.poll()

            #In case of error capture error properly
            if returncode:
                error_lines = [
                    line.decode().strip() for line in _proc.stderr.readlines()
                ]

        if returncode:  # i.e non zero return code
            raise Exception(
                "DataFlow failed with return code {} and error: {}".format(
                    _proc.returncode, "\n".join(error_lines)))

        logging.info("Launched dataflow job %s successfully and job id is:%s",
                     job_name, job_id)
        return job_id
    except Exception as e:
        raise AppExceptions.JobStartingException(e)


def get_dataflow_service():
    """Returns a Google Cloud Dataflow service object."""
    try:
        credentials, _ = google.auth.default()  #scopes=SCOPES
        return build('dataflow',
                     'v1b3',
                     credentials=credentials,
                     cache_discovery=False)
    except Exception as e:
        raise AppExceptions.DFServiceConnectionException(e)


def _sanitize_dataflow_job_name(job_name: str,
                                jobname_suffix_callables=None) -> str:
    """Sanitizes the job name and runs call backs to append suffixes"""
    base_job_name = str(job_name).replace('_', '-')

    if not re.match(r"^[a-z]([-a-z0-9]*[a-z0-9])?$", base_job_name):
        raise ValueError(
            'Invalid job_name ({}); the name must consist of'
            'only the characters [-a-z0-9], starting with a '
            'letter and ending with a letter or number '.format(base_job_name))

    # Check if any callables has provided in config to append suffix to job name such as date, uuid etc
    if jobname_suffix_callables:
        suffix = "-".join([
            func_name()
            for func_name in jobname_suffix_callables
            if callable(func_name)
        ])
        return f"{base_job_name}-{suffix}"

    return base_job_name


def poll_for_job_completion(df_service, location: str, project_id: str,
                            job_id: str):
    """Poll the job status every x seconds until done.
    https://cloud.google.com/dataflow/docs/reference/rest
    """
    job_state = None
    current_time = datetime.now()
    timeout_time = current_time + timedelta(seconds=TIMEOUT_IN_SECONDS)
    while job_state not in DataflowJobStates.END_STATES\
            and datetime.now() < timeout_time:
        try:
            logging.info(
                f'sleeping {POLLINTERVAL_IN_SECONDS} seconds before polling...')
            time.sleep(POLLINTERVAL_IN_SECONDS)
            pipeline_job = df_service.projects().locations().jobs().get(
                location=location, projectId=project_id,
                jobId=job_id).execute(num_retries=NUM_OF_RETRIES)
            job_state = pipeline_job['currentState']
            logging.info('Current job State is %s', job_state)
        except Exception as e:
            raise AppExceptions.JobPollingException(e)

    logging.info('Final Job State : %s', job_state)
    return job_state


def create_pipeline_configinstance(pipeline_name: str,
                                   pipeline_configuration: Dict[str, any]):
    # Create a class object based on the config dict keys
    PipelineConfig = namedtuple(pipeline_name, pipeline_configuration.keys())
    # Create an instance of PipelineConfig from dict values
    pipeline_config = PipelineConfig(**pipeline_configuration)
    return pipeline_config


def _build_cmd(location: str, project_id: str, executable: List[str],
               options: Dict[str, str]) -> List[str]:
    """Build command to execute as child process"""
    command = executable + [f"--project={project_id}", f"--region={location}", f"--runner={PIPELINE_RUNNER}"]

    if options:
        for name, value in options.items():
            if not value or isinstance(value, bool):
                command.append(f"--{name}")
            elif isinstance(value, list):
                command.extend([f"--{name}={v}" for v in value])
            else:
                command.append(f"--{name}={value}")
    return command


def has_callback(callbacks: Dict[str, Callable], status: str):
    """Check if pipeline has any call backs for corresponding job status"""
    return status in callbacks and callable(callbacks[status])


def run_callbacks(job_name: str, job_state: str,
                  callbacks: Dict[str, Callable]) -> None:
    """Checks the current Job State and executes appropriate call backs"""
    try:
        if job_state == DataflowJobStates.JOB_STATE_FAILED and has_callback(
                callbacks, "failure"):
            (callbacks["failure"])()
        elif job_state == DataflowJobStates.JOB_STATE_DONE and has_callback(
                callbacks, "success"):
            (callbacks["success"])()

        # Run onComplete call back whether job completes or succeeds
        if has_callback(
                callbacks,
                "complete") and job_state in DataflowJobStates.COMPLETE_STATES:
            (callbacks["complete"])()

        logging.info("Google Cloud Dataflow job {} ended with state: {}".format(
            job_name, job_state))
    except Exception as e:
        raise AppExceptions.CallbacksException(e)


def get_python_executable(python_interpretor: str, pipeline_config) -> List[str]:
    """Build python executable command"""
    exec_options = ["-m"]
    if hasattr(pipeline_config, "execoptions"):
        exec_options = pipeline_config.execoptions

    return [python_interpretor] + exec_options + [pipeline_config.pipelinemodule]


def get_java_executable(javaexec: str, pipeline_config) -> str:
    """Build Java executable command"""
    exec_options = ""
    if hasattr(pipeline_config, "execoptions"):
        exec_options = pipeline_config.execoptions

    if hasattr(pipeline_config, "classname"):
        return " ".join(
            [javaexec, "-cp", pipeline_config.jar, pipeline_config.classname])

    return " ".join([javaexec, exec_options, "-jar", pipeline_config.jar])


def main():
    """"Driver function to parse command line args, build pipeline options and invokes pipeline
    Flow:
    1. Read the pipleine config based on the pipeline name
    2. Build options and command
    3. Start data flow job and get job id
    4. If need to wait until job is done then poll for completion
    5. On completion based on status call the post processing steps if provided
    """
    cli_args = parse_cliargs()
    pipeline_config = create_pipeline_configinstance(
        cli_args.pipelinename, pipelineconfig.pipelines[cli_args.pipelinename]
    )
    job_options = deepcopy(pipelineconfig.common_options)
    job_options.update(pipeline_config.options)

    # Sanitize job name
    jobname_suffix_callables = pipeline_config.jobname_suffix if hasattr(
        pipeline_config, "jobname_suffix") else None
    job_options["job_name"] = _sanitize_dataflow_job_name(
        job_options["job_name"], jobname_suffix_callables)

    # Build executable based on the language
    if cli_args.language == "python":
        executable = get_python_executable(pipelineconfig.python_interpretor,
                                           pipeline_config)
    else:
        executable = get_java_executable("java", pipeline_config)

    # Build complete command along with options
    command = _build_cmd(pipelineconfig.location, pipelineconfig.project_id,
                         executable, job_options)

    try:
        job_id = _start_dfjob(job_options["job_name"],
                              pipeline_config.pipelinedir, command)

        if job_id and pipeline_config.waitUntilDone:
            # Monitor the job and run Post Processing steps
            df_service = get_dataflow_service()
            job_state = poll_for_job_completion(df_service,
                                                pipelineconfig.location,
                                                pipelineconfig.project_id,
                                                job_id)

            if hasattr(pipeline_config, "PostProcess"):
                run_callbacks(job_options["job_name"], job_state,
                              pipeline_config.PostProcess)
    except Exception as e:
        logging.error("Exception: Type:%s - Message: %s", type(e), str(e))



if __name__ == "__main__":
    logging.getLogger().setLevel(level=logging.INFO)
    main()
