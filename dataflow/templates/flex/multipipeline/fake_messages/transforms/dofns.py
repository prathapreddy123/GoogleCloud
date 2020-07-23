from faker import Faker
import json
import apache_beam as beam
from typing import Dict, Any
import pathlib
import yaml
import logging

@beam.typehints.with_input_types(int)
@beam.typehints.with_output_types(Dict[str, Any])
class GenerateFake(beam.DoFn):
    def __init__(self):
        self.config = None

    def start_bundle(self):
        #When package data exists
        #root_dir = pathlib.Path(__file__).parent.parent.resolve()
        #When data exists
        # root_dir = pathlib.Path(__file__).parent.parent.parent.resolve()
        #
        # file_path = pathlib.Path(root_dir,"conf/parameters.yaml").resolve()
        # logging.info("File Path: %s", file_path)
        # with open(file_path, 'r') as stream:
        #     self.config = yaml.safe_load(stream)
        self.config = yaml.safe_load("""
                                runtime: python37
                                beam: 2.19
                                dependecies:
                                    - Faker
                                    - pyYaml
                                """)

    def process(self, element, *args, **kwargs):
        fake = Faker()
        yield json.dumps({
            "id" : (element + 1)
           ,"name" : fake.name()
           ,"address" : fake.address()
          ,"runtime" : self.config["runtime"]
          ,"beam" : self.config["beam"]
          ,"dependecies" : ",".join(self.config["dependecies"])
        })

