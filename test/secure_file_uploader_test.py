import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from application import create_app

# Füge den Projektroot zum Python-Pfad hinzu
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

# Mock für das grp Modul
sys.modules['grp'] = Mock()
# Mock für das pwd Modul falls nötig
sys.modules['pwd'] = Mock()

from application.handler.SecureFileUploader import SecureFileUploader
from application import create_app, db

class TestSecureFileUploader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.putenv('APPLICATION_MODE', 'Test')
        """Einmalige Initialisierung vor allen Tests"""
        #pass

    def setUp(self):
        """Test-Setup vor jedem Testfall"""
        self.app = create_app()
        self.app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'WTF_CSRF_ENABLED': False
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Create all database tables
        db.create_all()
        with patch('paramiko.Transport'), \
             patch('paramiko.SFTPClient'):
            self.uploader = SecureFileUploader(self.test_db_uri)
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Aufräumen nach jedem Testfall"""
        """Cleanup after each test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

        if os.path.exists(self.test_dir):
            try:
                os.rmdir(self.test_dir)
            except OSError:
                pass

    @patch('socket.gethostbyname')
    def test_check_network(self, mock_gethostbyname):
        """Test der Netzwerkverbindungsprüfung"""
        # Test erfolgreiche Verbindung
        mock_gethostbyname.return_value = "192.168.1.1"
        ip = self.uploader.check_network()
        self.assertEqual(ip, "192.168.1.1")
        self.assertFalse(self.uploader.server_not_found)

        # Test fehlgeschlagene Verbindung
        mock_gethostbyname.side_effect = Exception()
        ip = self.uploader.check_network()
        self.assertTrue(self.uploader.server_not_found)


if __name__ == '__main__':
    unittest.main()