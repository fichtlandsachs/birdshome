import os
import sys
import unittest
from unittest.mock import Mock, patch

# Füge den Projektroot zum Python-Pfad hinzu
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

from application.handler.video_socket_2 import VideoSocket


class TestVideoSocket(unittest.TestCase):
    def setUp(self):
        self.test_db_uri = "sqlite:///:memory:"
        with patch('application.handler.video_socket_2.Picamera2'):
            self.video_socket = VideoSocket(self.test_db_uri)

    def test_get_configuration(self):
        """Test der Konfigurationsabfrage"""
        with patch('application.handler.video_socket_2.DBHandler') as mock_db:
            mock_db.return_value.get_config_entry.side_effect = [
                "15",  # VIDEO_DURATION
                "%Y%m%d_%H%M%S",  # TIME_FORMAT
                ".mp4",  # VIDEO_FORMAT
                "/videos",  # VIDEO_FOLDER
                "10",  # SENSITIVITY
                "15",  # DURATION
                "0"  # GRAYSCALE_ENABLED
            ]

            self.video_socket.get_configuration()
            self.assertEqual(self.video_socket.video_duration, 15)
            self.assertEqual(self.video_socket.sensitivity, 10)

    @patch('application.handler.video_socket_2.Picamera2')
    def test_create_video(self, mock_picam):
        """Test der Videoerstellung"""
        self.video_socket.cam_available = True
        test_filename = "test_video.mp4"

        self.video_socket.create_video(test_filename)
        mock_picam.return_value.start_recording.assert_called_once()
        mock_picam.return_value.stop_encoder.assert_called_once()


if __name__ == '__main__':
    unittest.main()