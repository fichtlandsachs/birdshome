import os
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

from app import app, _clean_folder  # passe den Import an


class MyAppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_personas_get(self):
        response = self.client.get('/personas')
        self.assertEqual(response.status_code, 200)
        #self.assertIn(b'personas.html', response.data)

    def test_capture_video_redirect(self):
        response = self.client.get('/capture_video', follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_video_feed_response(self):
        with mock.patch('myapp.appl.get_streaming_socket') as mock_get_socket, \
             mock.patch('myapp.appl.get_streaming_image') as mock_get_image:
            mock_get_socket.return_value = ('dummy_socket', 1024)
            dummy_image = np.zeros((10, 10, 3), dtype=np.uint8)
            mock_get_image.return_value = dummy_image
            response = self.client.get('/video_feed')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Content-Type: image/jpeg', response.data[:100])

    def test_clean_folder_creates_folder(self):
        temp_dir = tempfile.mkdtemp()
        os.rmdir(temp_dir)  # löschen, um Neuanlage zu erzwingen
        _clean_folder(temp_dir, 'test_')
        self.assertTrue(os.path.exists(temp_dir))
        os.rmdir(temp_dir)

if __name__ == '__main__':
    # Ermittle das Verzeichnis der aktuellen Datei (zum Beispiel Dein Test-Skript)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigiere zum Anwendungs-Root (hier ein Verzeichnis höher, passe den Pfad an Deine Struktur an)
    app_root = os.path.abspath(os.path.join(current_dir, '..'))
    # Füge den Anwendungsroot an den Anfang von sys.path ein
    sys.path.insert(0, app_root)
    unittest.main()
