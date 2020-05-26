import functools
import uuid
from datetime import datetime

import callbacks

project_id = "<project_id>"
location = "us-central1"
python_interpretor = "python3"
pipelinedir = "<pipelinedir>"
staging_location = "gs://<bucket>/staging/"
temp_location = "gs://<bucket>/temp/"


def get_timestamp(format: str = '%Y%m%d%H%M'):
    return datetime.now().strftime(format)


def get_uuid(length: int = 8):
    return str(uuid.uuid4())[:8]


common_options = {
    "staging_location": staging_location,
    "temp_location": temp_location,
    "setup_file": "./setup.py"
}

pipelines = {
    "fake_messages": {
        "pipelinedir": pipelinedir,
        "pipelinemodule": "pipelines.fake_messages",
        "options": {
            "job_name":
                "fake-messages",
            "message-count":
                1,
            "outputpath":
                "gs://<bucket>/output/fake_messages/sample"
        },
        "jobname_suffix": [
            functools.partial(get_timestamp, '%Y%m%d%H'), get_uuid
        ],
        "waitUntilDone": True,
        "PostProcess": {
            "success": callbacks.success,
            "failure": callbacks.failure
            #"complete": callbacks.complete
        }
    },
    "pubsubnotification": {
        "pipelinedir": pipelinedir,
        "pipelinemodule": "pipelines.pubsubnotification",
        "options": {
            "job_name":"pubsubnotification",
            "topicname":"page-history-topic",
            "outputbasepath":"gs://<bucket>/output/pubsubnotification"
        },
        "waitUntilDone": False,
        "PostProcess": {
            "success": callbacks.success,
            "failure": callbacks.failure
        }
    }
}
