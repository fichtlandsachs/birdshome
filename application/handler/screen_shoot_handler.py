import datetime
import os
import pathlib
import subprocess
import threading
from time import sleep

import cv2

import application as appl
import constants as constants
from application.handler.database_hndl import DBHandler, DatabaseChangeEvent


class ScreenShotHandler:
    def __init__(self, db_uri):

        self._lastRunScreenShot = None
        self._folder_screen_shots = None
        self._ending_picture = None
        self._time_format = None
        self._prefix_picture = None
        self._active = None
        self._intervall = None
        self._lastrun = None
        self._daysReplay = None
        self._lastRunReplay = None
        self._dbPath = db_uri
        self._dbHandler = DBHandler(db_uri)
        self._update_config()

    def _update_config(self):
        self._active = int(self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_ENABLED))
        self._intervall = int(self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_INTERVAL))
        self._lastRunScreenShot = self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_LAST_RUN_SCREEN)
        self._daysReplay = self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_DAYS)
        self._lastRunReplay = self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_LAST_STARTTIME)
        self._format_replay = self._dbHandler.get_config_entry(constants.REPLAY, constants.VID_FORMAT)
        self._prefix_replay = self._dbHandler.get_config_entry(constants.REPLAY, constants.REPLAY_PREFIX_VID)
        self._prefix_picture = self._dbHandler.get_config_entry(constants.PICTURE, constants.PREFIX_PIC)
        self._time_format = self._dbHandler.get_config_entry(constants.SYSTEM, constants.TIME_FORMAT_FILE)
        self._ending_picture = self._dbHandler.get_config_entry(constants.PICTURE, constants.ENDING_PIC)
        self._folder_screen_shots = self._dbHandler.get_config_entry(constants.REPLAY,
                                                                     constants.FOLDER_REPLAY_SCREENSHOT)

    def _create_screen_shot(self):
        file_name_short = self._prefix_picture + datetime.datetime.now().strftime(
            self._time_format) + '.' + str(self._ending_picture)
        full_filename = os.path.join(self._folder_screen_shots, file_name_short)

        client_socket, payload_size = appl.get_streaming_socket()
        image = appl.get_streaming_image(client_socket, payload_size)

        if len(image.shape) > 2:
            image_gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            image_gray = image
        cv2.imwrite(full_filename, image_gray)
        client_socket.close()

    def create_replay(self):
        screen_shots = list()
        pattern = '*.' + self._ending_picture
        screen_shots.extend(list(sorted(pathlib.Path(self._folder_screen_shots).glob(pattern), key=os.path.getmtime,
                                       reverse=True)))
        if len(screen_shots) > 0:
            return

        full_file_name = self._prefix_replay + self.lastrun.strftime(self._time_format) + self._format_replay
        ffmpeg_cmd = (
            f"ffmpeg -framerate 30 -pattern_type glob -i '{self._folder_screen_shots}/*.jpg' "
            f"-c:v libx264 '{full_file_name}'"
        )
        try:
            subprocess.run(ffmpeg_cmd, shell=True, check=True)
            for screen in screen_shots:
                os.remove(screen)
        except subprocess.CalledProcessError as e:
            print("Fehler beim Erstellen des Videos:", e)

    def start_replay_server(self):
        threading.Thread(target=self.start_replay, daemon=True).start()

    def start_replay(self):
        sleep(5)
        while True:
            if self._active == 1:
                if self._lastRunReplay is None:
                    self._dbHandler.create_update_config_entry(constants.REPLAY, constants.REPLAY_LAST_STARTTIME,
                                                               datetime.datetime.now().strftime(
                                                                   constants.DATETIME_FORMAT))
                    # self.lastRunReplay = self.app.config[constants.REPLAY_LAST_STARTTIME] = datetime.datetime.now().strftime(constants.DATETIME_FORMAT)
                if self._lastRunScreenShot is None:
                    self._create_screen_shot()
                    self._lastRunScreenShot = datetime.datetime.now().strftime(constants.DATETIME_FORMAT)
                    self._dbHandler.create_update_config_entry(constants.REPLAY, constants.REPLAY_LAST_RUN_SCREEN,
                                                               self._lastRunScreenShot)

                else:
                    self._lastrun = datetime.datetime.strptime(self._lastRunScreenShot, '%d.%m.%Y %H:%M:%S')
                    intervall = self._intervall * 60
                    next_run = self._lastrun + datetime.timedelta(seconds=intervall)
                    if next_run < datetime.datetime.now():
                        self._create_screen_shot()
                        self._dbHandler.create_update_config_entry(constants.REPLAY, constants.REPLAY_LAST_RUN_SCREEN,
                                                                   datetime.datetime.now().strftime(
                                                                    constants.DATETIME_FORMAT))
                if not self._dbHandler.check_config_entry_exists(app_area=constants.REPLAY,
                                                                 config_key=constants.REPLAY_LAST_STARTTIME):
                    self._dbHandler.create_update_config_entry(constants.REPLAY, constants.REPLAY_LAST_STARTTIME,
                                                               datetime.datetime.now().strftime(
                                                                   constants.DATETIME_FORMAT))

                next_replay_date = datetime.datetime.strptime(self._lastRunReplay,
                                                            '%d.%m.%Y %H:%M:%S') + datetime.timedelta(
                    seconds=86400)
                if next_replay_date < datetime.datetime.now():
                    self.create_replay()
                    self._dbHandler.create_update_config_entry(constants.REPLAY, constants.REPLAY_LAST_STARTTIME,
                                                               datetime.datetime.now().strftime(
                                                                   constants.DATETIME_FORMAT))
                sleep(self._intervall * 60)
            else:
                sleep(self._intervall * 60)

    def handle_database_event(self, event: DatabaseChangeEvent):
        self._update_config()
