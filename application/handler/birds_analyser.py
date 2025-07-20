import datetime
import logging
import os
import shutil
import threading
from logging.handlers import RotatingFileHandler

import cv2
from ultralytics import YOLO

import constants
from application.handler.database_hndl import DBHandler, DatabaseChangeEvent


class BirdVideoAnalyzer:
    """
    Diese Klasse analysiert alle Videos in einem angegebenen Verzeichnis.
    Für jedes Video wird überprüft, ob in ausgewählten Frames ein Vogel (Klasse "bird") erkannt wird.
    Falls in einem Video kein Vogel gefunden wird, wird die Datei in ein anderes Verzeichnis verschoben.
    """

    def __init__(self, _db_uri, session, model_path="yolov8n.pt", frame_interval=30, resize_factor=0.5):
        """

        :param model_path: der Pfad oder Name des vortrainierten YOLO‑Modells (Standard: YOLOv8n).
        :param frame_interval: Analysiert wird jeweils jeder n‑te Frame, um Rechenzeit zu sparen.
        :param resize_factor: Skalierungsfaktor, um die Frames vor der Analyse zu verkleinern.
        """
        self._db_url = _db_uri
        self._logger = logging.getLogger('BirdAnalyserLogger')
        self._logger.setLevel(logging.DEBUG)
        log_file = '/etc/birdshome/application/log/BirdVideoAnalyzer.log'
        logger_handler = RotatingFileHandler(filename=log_file, maxBytes=100000, backupCount=10)
        logger_handler.setLevel(logging.DEBUG)
        # Format für die Log-Meldungen definieren
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger_handler.setFormatter(formatter)
        # Handler dem Logger hinzufügen
        self._logger.addHandler(logger_handler)
        self._db_handler = DBHandler(_db_uri, session)
        self._output_dir_no_detect = ''
        self._input_dir = None
        self._output_dir_detect = self._db_handler.get_config_entry(constants.VIDEO, constants.FOLDER_VIDEOS_DETECT)
        self._output_dir_no_detect = self._db_handler.get_config_entry(constants.VIDEO,
                                                                       constants.FOLDER_VIDEOS_NO_DETECT)
        os.makedirs(self._output_dir_no_detect, exist_ok=True)
        os.makedirs(self._output_dir_detect, exist_ok=True)
        self._model = YOLO(model_path)
        self._frame_interval = frame_interval
        self._resize_factor = resize_factor
        self._delete_no_detect = 0
        self.get_configuration_data()

    def get_configuration_data(self):
        self._frame_interval = self._db_handler.get_config_entry(constants.VID_ANALYSER,
                                                                 constants.VID_ANALYSER_FRAME_DISTANCE)
        self._input_dir = self._db_handler.get_config_entry(constants.VIDEO, constants.FOLDER_VIDEOS)
        self._output_dir_no_detect = self._db_handler.get_config_entry(constants.VIDEO,
                                                                       constants.FOLDER_VIDEOS_NO_DETECT)
        self._output_dir_detect = self._db_handler.get_config_entry(constants.VIDEO, constants.FOLDER_VIDEOS_DETECT)
        self._delete_no_detect = self._db_handler.get_config_entry(constants.VID_ANALYSER,
                                                                   constants.DELETE_NO_DETECT_ENABLED)

    def detect_bird_in_video(self, video_path):
        """
        Öffnet ein Video, springt direkt zu jedem n‑ten Frame und verwendet das YOLO‑Modell,
        um zu prüfen, ob ein Vogel (Klasse "bird") erkannt wird.
        :param video_path: Pfad zur Videodatei.
        :return: Tuple (True, analysierte Frames), falls ein Vogel erkannt wird, sonst (False, analysierte Frames).
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_analysed = 0
        found_bird = False

        for frame_num in range(0, total_frames, int(self._frame_interval)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                break

            # Frame vor der Analyse verkleinern
            if self._resize_factor != 1.0:
                frame = cv2.resize(frame, None, fx=self._resize_factor, fy=self._resize_factor)

            frames_analysed += 1

            # YOLO‑Modell anwenden
            results = self._model(frame)
            for r in results:
                if r.boxes is not None and len(r.boxes) > 0:
                    # Überprüfe, ob ein Vogel (Klasse 14) erkannt wurde
                    cls_array = r.boxes.cls.cpu().numpy() if hasattr(r.boxes.cls, "cpu") else r.boxes.cls
                    if any(int(cls) == 14 for cls in cls_array):
                        found_bird = True
                        break
                if found_bird:
                    break
            if found_bird:
                break

        cap.release()
        return found_bird, frames_analysed

    def handle_database_event(self, event: DatabaseChangeEvent):
        self.get_configuration_data()

    def start_analyse_server(self):
        threading.Thread(target=self.analyze_videos).start()

    def analyze_videos(self):
        """
        Durchläuft alle Dateien im Eingabeverzeichnis, analysiert Videos und verschiebt jene,
        in denen keine Vögel erkannt wurden, in das Ausgabe‑Verzeichnis.
        """
        for filename in os.listdir(self._input_dir):
            video_path = os.path.join(self._input_dir, filename)
            if not os.path.isfile(video_path):
                continue
            # Nur Videodateien anhand der Endung verarbeiten
            if not any(video_path.lower().endswith(ext) for ext in [".mp4", ".avi", ".mkv", ".mov"]):
                continue

            self._logger.info(f"Analysiere Video: {filename}")
            result, frames = self.detect_bird_in_video(video_path)
            if not result:
                self._logger.info(f"Frames analysiert: {frames}")
                if self._delete_no_detect:
                    self._logger.info(f"Kein Vogel in {filename} gefunden. Lösche Datei.")
                    os.remove(video_path)
                else:
                    self._logger.info(f"Kein Vogel in {filename} gefunden. Verschiebe Datei.")
                    destination = os.path.join(self._output_dir_no_detect, filename)
                    shutil.move(video_path, destination)
            else:
                self._logger.info(f"Vogel in {filename} gefunden.")
                destination = os.path.join(self._output_dir_detect, filename)
                shutil.move(video_path, destination)


if __name__ == "__main__":
    # Beispielhafte Verzeichnisse; diese müssen existieren oder werden automatisch erstellt (für output_dir)
    db_uri = "sqlite:////etc/birdshome/application/database/birdshome.db"

    analyzer = BirdVideoAnalyzer(
        _db_uri=db_uri,
        frame_interval=30,  # Je nach Video-Frame-Rate kann dieser Wert weiter erhöht werden
        resize_factor=1.5
        # Anpassen, falls noch mehr Performance benötigt wird (allerdings auf Kosten der Erkennungsgenauigkeit)
    )
    start_time = datetime.datetime.now()
    analyzer.analyze_videos()
    end_time = datetime.datetime.now()
    duration = end_time - start_time
    print(f"Dauer der Analyse: {duration.strftime(constants.DATETIME_FORMAT)}")
