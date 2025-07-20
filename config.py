import os
import socket


class Config:
    """Base config vars."""
    DEBUG = False
    TESTING = False
    SECRET_KEY = ''
    USER_APP = 'pi'
    USER_GROUP = 'pi'
    """"Default configuration Server Upload"""
    SERVER_UPLOAD_ENABLED = 0
    DELETE_AFTER_UPLOAD_ENABLED = 0
    DELETE_NO_DETECT_ENABLED = 0
    KEEP_FILE_LOCAL = 5
    PAUSE_RETRY_UPLOAD = 5
    NUM_RETRY_UPLOAD = 3
    GRAYSCALE_ENABLED = 0
    # Server Upload parameters
    FTP_ENABLED = 0
    FTP_SERVER = ''
    FTP_SHARE = ''
    FTP_USER = ''
    FTP_PORT = 00
    FTP_PASSWORD = ''

    NEXT_CLOUD_ENABLED = 0
    NEXT_CLOUD_SERVER = ''
    NEXT_CLOUD_USER = ''
    NEXT_CLOUD_PASSWORD = ''
    NEXT_CLOUD_FOLDER = ''

    SMB_ENABLED = 1
    SMB_SERVER = ''
    SMB_USER = ''
    SMB_PASSWORD = ''
    SMB_SHARE = ''

    FILE_SHARE_ENABLED = 0
    FILE_SHARE_SERVER = ''
    FILE_SHARE_USER = ''
    FILE_SHARE_PASSWORD = ''
    FILE_SHARE_FOLDER = ''

    TIME_UPLOAD = '21:00'
    """"Default configuration Video"""
    DURATION_VID = 15
    PREFIX_VID = socket.gethostname() + '_'
    VID_RES_X = 640
    VID_RES_Y = 480
    VID_FRAMES = 30
    VID_FORMAT = '.mp4'
    SOUND_FORMAT = '.wav'
    VID_ENDINGS = ['*.mp4']
    VID_LABEL_FORMAT = '%d.%m.%Y %H:%M:%S'

    """Default replay Configuration"""
    REPLAY_ENABLED = False
    FRAMES_PER_SEC_REPLAY = 30
    REPLAY_INTERVAL = 10
    REPLAY_DAYS = 7
    REPLAY_PREFIX_VID = socket.gethostname() + '_'
    FOLDER_REPLAY = 'replay'
    FOLDER_REPLAY_SCREENSHOT = 'screenshots'
    """Default picture Configuration"""
    PREFIX_PIC = socket.gethostname() + '_'
    ENDING_PIC = 'jpg'
    LATEST_PIC_RES_X = '1280'
    LATEST_PIC_RES_Y = '720'

    VID_ANALYSER_TIME_RUN = '02:00'
    VID_ANALYSER_ENABLED = 0
    VID_ANALYSER_FRAME_DISTANCE = 30

    NAME_BIRD = ''
    DATE_CHICK = None
    DATE_EGG = None
    FIRST_VISIT = None
    DATE_LEAVE = None

    SENSITIVITY = 8
    KEY = ''

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = '/database/birdshome.db'

    OUTPUT_FOLDER = os.path.join('static')
    MEDIA_FOLDER = 'static/media'
    DATABASE_FOLDER = 'database'
    DATABASE_NAME = 'birdshome.db'
    FOLDER_PICTURES = 'photos'
    FOLDER_VIDEOS = 'videos'
    FOLDER_SCREENSHOTS = 'pictures'
    FOLDER_VIDEO_NO_DETECT = 'nodetect'
    FOLDER_VIDEO_DETECT = 'detect'
    FOLDER_PERSONAS = 'general'

    TIME_FORMAT_FILE = "%d%m%Y%H%M%S"
    TEMPLATES_AUTO_RELOAD = True


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
    FLASK_DEBUG = 0
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/birdshome/application/database/birdshome.db'

class TestConfig(Config):
    DEBUG = False
    TESTING = False
    FLASK_DEBUG = 1
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    FLASK_DEBUG = 1
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/birdshome/application/database/birdshome_dev.db'
