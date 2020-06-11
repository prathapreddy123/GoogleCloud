import unittest

from fake_messages.transforms import dofns
import pipeline

class TestDemo(unittest.TestCase):
    def test_name(self):
        self.assertEqual(pipeline.get_name("dataflow"), "hello dataflow")

    def test_fullname(self):
        self.assertEqual(dofns.join_names("flex", "template"), "flex template")
