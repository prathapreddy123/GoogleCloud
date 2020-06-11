import unittest

from fake_messages import fake_to_gcs

class TestDemo(unittest.TestCase):
    def test_name(self):
        self.assertEqual(fake_to_gcs.get_name("dataflow"), "hello dataflow")
