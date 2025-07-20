import datetime
import io
import logging
import os
import socket
import struct
import threading
import time
from logging.handlers import RotatingFileHandler

import numpy as np
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder
from picamera2.outputs import FileOutput, FfmpegOutput

import constants
from application.handler.database_hndl import DBHandler, DatabaseChangeEvent


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class VideoSocket:
    def __init__(self, db_uri):
        self.video_format = None
        self.db_uri = db_uri
        self.logger = logging.getLogger('VideoSocket')
        self.logger.setLevel(logging.DEBUG)
        log_file = '/etc/birdshome/application/log/VideoSocket.log'
        logger_handler = RotatingFileHandler(filename=log_file, maxBytes=100000, backupCount=10)
        logger_handler.setLevel(logging.DEBUG)
        # Format für die Log-Meldungen definieren
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger_handler.setFormatter(formatter)
        # Handler dem Logger hinzufügen
        self.logger.addHandler(logger_handler)
        self.lsize = (640, 480)
        self.db_handler = DBHandler(self.db_uri)
        self.grayscale_enabled = 0
        self.cam_available = False
        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"size": self.lsize, "format": "RGB888"},
                lores={"size": (640, 480), "format": "YUV420"}
            )
            self.logger.debug(f"main size: {self.lsize} format=RGB888")
            self.logger.debug(f"lores size: {640, 480} format=YUV420")
            self.picam2.configure(config)
            self.cam_available = True
        except Exception as e:
            self.logger.error(e)
            self.cam_available = False
        self.output_stream = StreamingOutput()
        self.streaming_encoder = MJPEGEncoder()
        self.video_encoder = H264Encoder(framerate=30, iperiod=30, bitrate=10000000)
        self.video_duration = None
        self.time_format = None
        self.output_folder = None
        self.sensitivity = 10
        self.duration = 15
        self.get_configuration()

    def handle_database_event(self, event: DatabaseChangeEvent):
        self.get_configuration()

    def get_configuration(self):
        db_handler = DBHandler(self.db_uri)
        self.video_duration = int(db_handler.get_config_entry(constants.VIDEO, constants.DURATION_VID))
        self.time_format = db_handler.get_config_entry(constants.SYSTEM, constants.TIME_FORMAT_FILE)
        self.video_format = db_handler.get_config_entry(constants.VIDEO, constants.VID_FORMAT)
        self.output_folder = db_handler.get_config_entry(constants.VIDEO, constants.FOLDER_VIDEOS)
        self.sensitivity = int(db_handler.get_config_entry(constants.SYSTEM, constants.SENSITIVITY))
        self.duration = int(db_handler.get_config_entry(constants.VIDEO, constants.DURATION_VID))
        self.grayscale_enabled = int(self.db_handler.get_config_entry(constants.SYSTEM, constants.GRAYSCALE_ENABLED))
        if self.cam_available:
            if self.grayscale_enabled == 1:
                self.picam2.set_controls({"Saturation": 0.0})
                self.logger.info(f"set grayscale enabled")
            else:
                self.picam2.set_controls({"Saturation": 1.0})
                self.logger.info(f"remove grayscale enabled")
        else:
            self.logger.warning("camera not available")
        db_handler.close()

    def client_handler(self, client_socket, addr):
        """Sendet kontinuierlich den aktuell erfassten Frame an den verbundenen Client."""
        self.logger.debug(f"Client {addr} verbunden.")
        try:
            while True:
                with self.output_stream.condition:
                    self.output_stream.condition.wait()
                    frame_data = self.output_stream.frame
                    # Verpacke die Daten: 4 Byte für die Länge gefolgt von den JPEG-Daten
                    message = struct.pack(">L", len(frame_data)) + frame_data
                    client_socket.sendall(message)
                # Wartezeit, um die Übertragungsrate zu steuern
                time.sleep(0.03)
        except Exception as e:
            self.logger.debug(f"Client {addr} getrennt: {e}")
        finally:
            client_socket.close()

    def start_server(self, host='0.0.0.0', port=9999):
        """Startet einen TCP-Server, der eingehende Client-Verbindungen akzeptiert."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(10)
        self.logger.info(f"Server gestartet auf {host}:{port}")
        self.output_stream = StreamingOutput()
        if self.cam_available:
            self.picam2.start_recording(self.streaming_encoder, FileOutput(self.output_stream))
            while True:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=self.client_handler, args=(client_socket, addr), daemon=True).start()

    def recording_file_names(self):
        timestamp_file = datetime.datetime.now().strftime(self.time_format)
        full_file_name = os.path.join(self.output_folder, timestamp_file + self.video_format)
        return full_file_name

    def motion_handling(self):
        cur = None
        prev = None
        encoding = False
        ltime = 0
        self.get_configuration()
        while True:
            if self.cam_available:
                cur = self.picam2.capture_buffer("lores")
                if prev is not None:
                    mse = np.square(np.subtract(cur, prev)).mean()
                    if mse > self.sensitivity:
                        full_file_name = self.recording_file_names()
                        self.logger.info(f"start video recording due of movement")
                        self.create_video(full_file_name)
                        ltime = time.time()
                    else:
                        if encoding and time.time() - ltime > 2.0:
                            self.picam2.stop_encoder()
                            encoding = False
            prev = cur
            time.sleep(0.33)

    def create_video(self, full_file_name):
        output = FfmpegOutput(output_filename=f"{full_file_name}",
                              audio_bitrate=44100,
                              audio_codec='aac',
                              audio=True,
                              audio_sync=-.4,
                              audio_filter="pan=stereo|c0=c0|c1=c0"
                              )
        if self.cam_available:
            self.picam2.start_recording(self.video_encoder, output)
            time.sleep(self.duration)
            self.picam2.stop_encoder(self.video_encoder)
        else:
            self.logger.warning("camera not available")

    def start_socket(self):
        # Starte Capture- und Motion-Handling-Threads
        threading.Thread(target=self.motion_handling, daemon=True).start()
        # Starte den Server, der auf Client-Verbindungen wartet
        threading.Thread(target=self.start_server, daemon=True).start()
