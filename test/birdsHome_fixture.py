
import unittest

from application import create_app


class birdshome_fixture(unittest.TestSuite):

    def __init__(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()