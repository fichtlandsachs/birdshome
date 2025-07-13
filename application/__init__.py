import os
import socket
import struct
from grp import getgrnam
from logging.handlers import RotatingFileHandler
from pwd import getpwnam

import cv2
import flask
import numpy as np
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import constants
from config import Config as CFG, DevConfig, ProdConfig


class SocketReader:
    """
    Ein einfacher File-Like-Wrapper um einen Socket,
    der nur die read()-Methode benötigt.
    """

    def __init__(self, sock):
        self.sock = sock

    def read(self, n):
        """Liest genau n Bytes vom Socket."""
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                break
            data += chunk
        return data

    def write(self, data):
        return self.sock.send(data)

    def flush(self):
        pass


db = SQLAlchemy()
appConfigKeys = [
    [constants.PICTURE, constants.ENDING_PIC],
    [constants.PICTURE, constants.PREFIX_PIC],
    [constants.PICTURE, constants.LATEST_PIC_RES_X],
    [constants.PICTURE, constants.LATEST_PIC_RES_Y],

    [constants.VIDEO, constants.DURATION_VID],
    [constants.VIDEO, constants.PREFIX_VID],
    [constants.VIDEO, constants.VID_RES_X],
    [constants.VIDEO, constants.VID_RES_Y],
    [constants.VIDEO, constants.VID_FRAMES],
    [constants.VIDEO, constants.VID_LABEL_FORMAT],
    [constants.VIDEO, constants.VID_FORMAT],
    [constants.VIDEO, constants.TIME_FORMAT_FILE],
    [constants.VIDEO, constants.FOLDER_VIDEOS],
    [constants.VIDEO, constants.FOLDER_VIDEOS_NO_DETECT],
    [constants.VIDEO, constants.FOLDER_VIDEOS_DETECT],

    [constants.REPLAY, constants.REPLAY_PREFIX_VID],
    [constants.REPLAY, constants.FRAMES_PER_SEC_REPLAY],
    [constants.REPLAY, constants.REPLAY_INTERVAL],
    [constants.REPLAY, constants.REPLAY_DAYS],
    [constants.REPLAY, constants.REPLAY_ENABLED],
    [constants.REPLAY, constants.FOLDER_REPLAY_SCREENSHOT],
    [constants.REPLAY, constants.FOLDER_REPLAY],

    [constants.VID_ANALYSER, constants.VID_ANALYSER_TIME_RUN],
    [constants.VID_ANALYSER, constants.VID_ANALYSER_FRAME_DISTANCE],
    [constants.VID_ANALYSER, constants.VID_ANALYSER_ENABLED],
    [constants.VID_ANALYSER, constants.DELETE_NO_DETECT_ENABLED],
    [constants.SMB, constants.SERVER_UPLOAD_ENABLED],
    [constants.SMB, constants.DELETE_AFTER_UPLOAD_ENABLED],

    [constants.SMB, constants.KEEP_FILE_LOCAL],
    [constants.SMB, constants.TIME_UPLOAD],

    [constants.SMB, constants.SMB_ENABLED],
    [constants.SMB, constants.SMB_SERVER],
    [constants.SMB, constants.SMB_USER],
    [constants.SMB, constants.SMB_PASSWORD],
    [constants.SMB, constants.SMB_SHARE],

    [constants.FTP, constants.FTP_ENABLED],
    [constants.FTP, constants.FTP_SERVER],
    [constants.FTP, constants.FTP_USER],
    [constants.FTP, constants.FTP_PASSWORD],
    [constants.FTP, constants.FTP_PORT],
    [constants.FTP, constants.FTP_SHARE],

    [constants.NEXT_CLOUD, constants.NEXT_CLOUD_ENABLED],
    [constants.NEXT_CLOUD, constants.NEXT_CLOUD_SERVER],
    [constants.NEXT_CLOUD, constants.NEXT_CLOUD_USER],
    [constants.NEXT_CLOUD, constants.NEXT_CLOUD_PASSWORD],
    [constants.NEXT_CLOUD, constants.NEXT_CLOUD_FOLDER],

    [constants.SYSTEM, constants.TIME_FORMAT_FILE],
    [constants.SYSTEM, constants.SENSITIVITY],
    [constants.SYSTEM, constants.GRAYSCALE_ENABLED],
    [constants.SYSTEM, constants.FOLDER_MEDIA],
    [constants.SYSTEM, constants.FOLDER_PICTURES],
    [constants.SYSTEM, constants.FOLDER_PERSONAS],

    [constants.NEST_CONFIG, constants.FIRST_VISIT],
    [constants.NEST_CONFIG, constants.DATE_EGG],
    [constants.NEST_CONFIG, constants.DATE_CHICK],
    [constants.NEST_CONFIG, constants.DATE_LEAVE],
    [constants.NEST_CONFIG, constants.NAME_BIRD]
]


def get_configuration_data(app: flask.app):
    mode = os.getenv('APPLICATION_MODE')
    if mode == 'DEV':
        app.config.from_object(DevConfig())
    else:
        app.config.from_object(ProdConfig())
    # updateConfiguration(app)

def create_folder_structure(app):
    user_uuid = getpwnam(CFG.USER_APP)[2]
    grp_uuid = getgrnam(CFG.USER_GROUP)[2]

    path_media = os.path.join(app.root_path, CFG.MEDIA_FOLDER)
    path_database = os.path.join(app.root_path, CFG.DATABASE_FOLDER)
    database_name = os.path.join(app.root_path, CFG.DATABASE_FOLDER, CFG.DATABASE_NAME)
    path_video = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_VIDEOS)
    path_video_detect = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_VIDEOS, CFG.FOLDER_VIDEO_DETECT)
    path_video_no_detect = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_VIDEOS, CFG.FOLDER_VIDEO_NO_DETECT)
    path_pictures = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_PICTURES)
    path_replay = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_REPLAY)
    path_replay_screens = os.path.join(path_replay, CFG.FOLDER_REPLAY_SCREENSHOT)
    path_general = os.path.join(app.root_path, CFG.MEDIA_FOLDER, CFG.FOLDER_PERSONAS)

    app.config[constants.FOLDER_MEDIA] = path_media
    app.config[constants.FOLDER_VIDEOS] = path_video
    app.config[constants.FOLDER_VIDEOS_NO_DETECT] = path_video_no_detect
    app.config[constants.FOLDER_VIDEOS_DETECT] = path_video_detect
    app.config[constants.FOLDER_PICTURES] = path_pictures
    app.config[constants.FOLDER_REPLAY] = path_replay
    app.config[constants.FOLDER_REPLAY_SCREENSHOT] = path_replay_screens
    app.config[constants.FOLDER_PERSONAS] = path_general
    app.config[constants.SQLALCHEMY_DATABASE_URI] = 'sqlite:///' + database_name

    if not os.path.exists(path_media):
        os.makedirs(path_media)
        os.chown(path_media, user_uuid, grp_uuid)
        app.logger.info('Path media folder created at ' + path_media)
    if not os.path.exists(path_database):
        os.makedirs(path_database)
        os.chown(path_database, user_uuid, grp_uuid)
        app.logger.info('Path datebase folder created at ' + path_database)
    if not os.path.exists(path_video):
        os.makedirs(path_video)
        os.chown(path_video, user_uuid, grp_uuid)
        app.logger.info('Path video folder created at ' + path_video)
    if not os.path.exists(path_video_detect):
        os.makedirs(path_video_detect)
        os.chown(path_video_detect, user_uuid, grp_uuid)
        app.logger.info('Path video detect folder created at ' + path_video_detect)
    if not os.path.exists(path_video_no_detect):
        os.makedirs(path_video_no_detect)
        os.chown(path_video_no_detect, user_uuid, grp_uuid)
        app.logger.info('Path no_detect folder created at ' + path_video_no_detect)
    if not os.path.exists(path_pictures):
        os.makedirs(path_pictures)
        os.chown(path_pictures, user_uuid, grp_uuid)
        app.logger.info('Path picture folder created at ' + path_pictures)
    if not os.path.exists(path_replay):
        os.makedirs(path_replay)
        os.chown(path_replay, user_uuid, grp_uuid)
        app.logger.info('Path replay folder created at ' + path_replay)
    if not os.path.exists(path_replay_screens):
        os.makedirs(path_replay_screens)
        os.chown(path_replay_screens, user_uuid, grp_uuid)
        app.logger.info('Path replay_screenshots folder created at ' + path_replay_screens)
    if not os.path.exists(path_general):
        os.makedirs(path_general)
        os.chown(path_general, user_uuid, grp_uuid)
        app.logger.info('Path general folder created at ' + path_general)

def create_app():
    """Construct the core application."""
    """
    1. Erzeugen der Flask Instanz
    2. Einlesen de Config Files
    3. Erstellen der Datenbank und des Datenbankschemas
    4. Ablegen der Konfiguration in der Datenbank
    5. Aktualisieren der App Konfiguration mit Konfigurationswerten
    """
    app = Flask(__name__, instance_relative_config=True)
    get_configuration_data(app=app)
    log_file = os.path.join(app.root_path, 'log/birdshome.log')
    app.logger.addHandler(RotatingFileHandler(filename=log_file, maxBytes=100000, backupCount=10))

    create_folder_structure(app=app)

    db.init_app(app)
    app.app_context().push()
    with app.app_context():
        from . import models
        from . import routes
        engine = db.create_engine(url=app.config[constants.SQLALCHEMY_DATABASE_URI])
        db.metadata.create_all(bind=engine, checkfirst=True)
        app = update_configuration(app)

    return app


def update_configuration(_app):
    from application.handler.database_hndl import DBHandler
    update_setup(_app)
    _db = DBHandler(_app.config[constants.SQLALCHEMY_DATABASE_URI])
    for entry in appConfigKeys:
        _app.config[entry[1]] = _db.get_config_entry(entry[0], entry[1])
    return _app


def update_setup(_app):
    from application.handler.database_hndl import DBHandler
    _db = DBHandler(_app.config[constants.SQLALCHEMY_DATABASE_URI])
    for entry in appConfigKeys:
        if not _db.check_config_entry_exists(entry[0], entry[1]):
            _db.create_update_config_entry(entry[0], entry[1], _app.config[entry[1]])
        else:
            _app.config[entry[1]] = _db.get_config_entry(entry[0], entry[1])


def write_setup(_app):
    from application.handler.database_hndl import DBHandler
    _db = DBHandler(_app.config[constants.SQLALCHEMY_DATABASE_URI])
    for entry in appConfigKeys:
        _db.create_update_config_entry(entry[0], entry[1], _app.config[entry[1]])


def recvall(sock, count):
    """Empfängt genau 'count' Bytes vom Socket."""
    buf = b''
    while count:
        newbuf = sock.recv(count)
        if not newbuf:
            return None
        buf += newbuf
        count -= len(newbuf)
    return buf


def video_streaming_frame(client_socket, payload_size):
    frame_data = None
    # Empfange die 4-Byte-Länge des kommenden Frames
    packed_msg_size = recvall(client_socket, payload_size)
    if packed_msg_size:
        msg_size = struct.unpack(">L", packed_msg_size)[0]
        # Empfange den kompletten Frame-Datenblock
        frame_data = recvall(client_socket, msg_size)
        if frame_data is None:
            frame_data = None

    # Deserialisiere den Frame (JPEG als numpy-Array per pickle)
    # frame = pickle.loads(frame_data)
    return frame_data


def get_streaming_socket():
    server_ip = '127.0.0.1'
    server_port = 9999
    # """Video streaming generator function."""
    """Verbindet sich mit dem Server, empfängt Frames und zeigt sie mit OpenCV an."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))

    payload_size = struct.calcsize(">L")
    return client_socket, payload_size


def get_streaming_image(client_socket, payload_size):
    image = None
    frame = video_streaming_frame(client_socket, payload_size)
    if frame is not None:
        np_arr = np.frombuffer(frame, dtype=np.uint8)
        if np_arr is None:
            return None
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image


def get_streaming_frame(client_socket, payload_size):
    frame = video_streaming_frame(client_socket, payload_size)
    if frame is None:
        return None
    else:
        frame = np.frombuffer(frame, dtype=np.uint8)
    image = cv2.imdecode(frame, cv2.IMREAD_COLOR)
    return image


def create_video():
    client_socket, _ = get_streaming_socket()
    client_socket.sendall('create_video'.encode('utf-8'))
