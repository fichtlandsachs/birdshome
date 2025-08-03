import logging
import os
import socket


class Config:
    """Base config vars."""
    DEBUG:bool = False
    TESTING:bool = False
    SECRET_KEY:str = ''
    USER_APP:str = 'pi'
    USER_GROUP:str = 'pi'
    """"Default configuration Server Upload"""
    SERVER_UPLOAD_ENABLED:bool = False
    DELETE_AFTER_UPLOAD_ENABLED:bool = False
    DELETE_NO_DETECT_ENABLED:bool = False
    KEEP_FILE_LOCAL:int = 5
    PAUSE_RETRY_UPLOAD:int = 5
    NUM_RETRY_UPLOAD:int = 3
    GRAYSCALE_ENABLED:bool = False
    # Server Upload parameters
    FTP_ENABLED:bool = False
    FTP_SERVER:str = ''
    FTP_SHARE:str = ''
    FTP_USER:str = ''
    FTP_PORT:int = 00
    FTP_PASSWORD:str = ''

    NEXT_CLOUD_ENABLED:bool = False
    NEXT_CLOUD_SERVER:str = ''
    NEXT_CLOUD_USER:str = ''
    NEXT_CLOUD_PASSWORD:str = ''
    NEXT_CLOUD_FOLDER:str = ''

    SMB_ENABLED:bool = False
    SMB_SERVER:str = ''
    SMB_USER:str = ''
    SMB_PASSWORD:str = ''
    SMB_SHARE:str = ''

    FILE_SHARE_ENABLED:bool = False
    FILE_SHARE_SERVER:str = ''
    FILE_SHARE_USER:str = ''
    FILE_SHARE_PASSWORD:str = ''
    FILE_SHARE_FOLDER:str = ''

    TIME_UPLOAD = '21:00'
    """"Default configuration Video"""
    DURATION_VID:int = 15
    PREFIX_VID:str = socket.gethostname() + '_'
    VID_RES_X:int = 640
    VID_RES_Y:int = 480
    VID_FRAMES:int = 30
    VID_FORMAT:str = '.mp4'
    SOUND_FORMAT:str = '.wav'
    VID_ENDINGS = ['*.mp4']
    VID_LABEL_FORMAT:str = '%d.%m.%Y %H:%M:%S'

    """Default replay Configuration"""
    REPLAY_ENABLED:bool = False
    FRAMES_PER_SEC_REPLAY:int = 30
    REPLAY_INTERVAL:int = 10
    REPLAY_DAYS:int = 7
    REPLAY_PREFIX_VID:str = socket.gethostname() + '_'
    FOLDER_REPLAY:str = 'replay'
    FOLDER_REPLAY_SCREENSHOT:str = 'screenshots'
    """Default picture Configuration"""
    PREFIX_PIC = socket.gethostname() + '_'
    ENDING_PIC = 'jpg'
    LATEST_PIC_RES_X:str = '1280'
    LATEST_PIC_RES_Y:str = '720'

    VID_ANALYSER_TIME_RUN = '02:00'
    VID_ANALYSER_ENABLED:bool = False
    VID_ANALYSER_FRAME_DISTANCE:int = 30

    NAME_BIRD:str = ''
    DATE_CHICK = None
    DATE_EGG = None
    FIRST_VISIT = None
    DATE_LEAVE = None

    SENSITIVITY:int = 10
    KEY:str = ''

    SQLALCHEMY_TRACK_MODIFICATIONS:bool = False
    #SQLALCHEMY_DATABASE_URI = '/database/birdshome.db'

    OUTPUT_FOLDER:str = os.path.join('static')
    FOLDER_MEDIA:str = 'static/media'
    DATABASE_FOLDER:str = 'database'
    DATABASE_NAME:str = 'birdshome.db'
    FOLDER_PICTURES:str = 'photos'
    FOLDER_VIDEOS:str = 'videos'
    FOLDER_VIDEOS_NO_DETECT:str = 'nodetect'
    FOLDER_VIDEOS_DETECT:str = 'detect'
    FOLDER_PERSONAS:str = 'general'
    LOG_LOCATION:str = '/var/log/birdshome'
    LOG_FORMAT:str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_LEVEL:int = logging.ERROR

    TIME_FORMAT_FILE:str = "%d%m%Y%H%M%S"
    TEMPLATES_AUTO_RELOAD:bool = True


class ProdConfig(Config):
    DEBUG:bool = False
    TESTING:bool = False
    FLASK_DEBUG:bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS:bool = False
    SQLALCHEMY_DATABASE_URI:str = 'sqlite:////etc/birdshome/application/database/birdshome.db'

class TestConfig(Config):
    DEBUG:bool = True
    TESTING:bool = True
    FLASK_DEBUG:bool = False
    SQLALCHEMY_TRACK_MODIFICATIONS:bool = True
    SQLALCHEMY_DATABASE_URI:str = 'sqlite:////etc/birdshome/application/database/birdshome_test.db'


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    FLASK_DEBUG = 1
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:////etc/birdshome/application/database/birdshome_dev.db'
