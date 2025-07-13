import unittest

from application.handler.SecureFileUploader import SecureFileUploader


class SecureFileUploaderTestcase(unittest.TestCase):
    def test_init(self):
        sec_uploader = SecureFileUploader(db_uri='sqlite:////etc/birdshome/application/database/birdshome.db')

        self.assertIsNotNone(sec_uploader._dbHandler)  # add assertion here
        sec_uploader._time_upload = '10:00'
        sec_uploader.upload()


if __name__ == '__main__':
    unittest.main()
