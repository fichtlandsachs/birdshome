import os
import sys
import threading
import unittest
from unittest.mock import patch

from app import video_socket

# Füge den Projektroot zum Python-Pfad hinzu
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)
import application as appl
from application.handler.video_socket_2 import VideoSocket
from application import create_app, constants

class TestVideoSocket(unittest.TestCase):
    def __init__(self, method_name: str = "runTest"):
        super().__init__(method_name)

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def test_start_server(self):
        client_socket, payload_size = appl.get_streaming_socket()
        self.assertIsNotNone(client_socket)
        image = appl.get_streaming_image(client_socket, payload_size)
        self.assertIsNotNone(image)
        client_socket.close()



if __name__ == '__main__':
    unittest.main()