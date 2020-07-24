"""
Batch pipeline that generates fake messages and writes records to GCS
"""

import apache_beam as beam
from apache_beam.options.pipeline_options import (PipelineOptions, SetupOptions, StandardOptions)
from typing import Tuple, List
import argparse
import logging
from fake_messages.common import config
from fake_messages.transforms import dofns



def parse_cliargs(argv) -> Tuple[argparse.Namespace, List[str]]:
    """"Parses Command line args

      Args: None

      Returns:
          Tuple containing Namespace object with specified arguments and list of extra arguments
  """
    args_parser = argparse.ArgumentParser(argv)

    args_parser.add_argument('--message-count',
                             type=int,
                             help="Number of messages",
                             required=True)

    args_parser.add_argument('--output-path',
                             type=str,
                             help="Output path",
                             required=True)
    return args_parser.parse_known_args()

def run(argv: List[str] = None, save_main_session: bool = True) -> None:
    """"Driver function to parse command line args, build pipeline options and invokes pipeline

      Args:
          user_args: Command line arguments specified by the user
          pipeline_options: Dataflow Pipeline options

      Returns:
          None
  """
    logging.info("Running pipeline to generate fake messages...")
    user_args, extra_args = parse_cliargs(argv)
    pipeline_options = PipelineOptions()
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session
    pipeline = beam.Pipeline(options=pipeline_options)

    (pipeline
         | 'Read data' >> beam.Create([i for i in range(user_args.message_count)])
         | 'Generate fake data' >> beam.ParDo(dofns.GenerateFake())
         | 'Write data to GCS' >>  beam.io.WriteToText(user_args.output_path, file_name_suffix=config.file_extension,num_shards=config.num_shards)   #beam.Map(print) #
    )

    pipeline_result = pipeline.run()

   # Used while testing locally
    if pipeline_options.view_as(StandardOptions).runner == "DirectRunner":
        pipeline_result.wait_until_finish()

def get_name(name):
    return "hello " + name;


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    run()
