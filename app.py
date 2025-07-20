import datetime
import glob
import io
import os
import pathlib
import sqlite3
import threading
import time

import numpy as np
from cryptography.fernet import Fernet
from flask import render_template, Response, g, request, redirect, url_for

import application as appl
import constants
from application import create_app, update_setup
from application.forms.admin_form import AdminForm
from application.handler.database_hndl import DBHandler, DatabaseEventHandler, DatabaseChangeEvent
from application.handler.video_socket_2 import VideoSocket

import cv2

app = create_app()
if app is None:
    exit(1)

with app.app_context():
    DATABASE = app.config[constants.SQLALCHEMY_DATABASE_URI]

from application.handler.screen_shoot_handler import ScreenShotHandler
from application.handler.SecureFileUploader import SecureFileUploader
from application.handler.birds_analyser import BirdVideoAnalyzer

app.config['EVENT_HANDLERS'] = DatabaseEventHandler()


def get_db():
    _db = getattr(g, '_database', None)
    if _db is None:
        _db = g._database = sqlite3.connect(DATABASE)
    return _db

with app.app_context():
    app.logger.info('Start Video_socket')
    video_socket = VideoSocket(db_uri=app.config[constants.SQLALCHEMY_DATABASE_URI], session=app.config[constants.DB_SESSION])
    app.config[constants.EVENT_HANDLERS].register_listener(video_socket)
    thread_video = threading.Thread(target=video_socket.start_socket())
    thread_video.start()

time.sleep(5)
with app.app_context():
    app.logger.info('Start ReplayTask')
    replay_socket = ScreenShotHandler(db_uri=app.config[constants.SQLALCHEMY_DATABASE_URI], session=app.config[constants.DB_SESSION])
    app.config[constants.EVENT_HANDLERS].register_listener(replay_socket)
    replay_socket.start_replay_server()

with app.app_context():
    app.logger.info('Start FileUploader')
    file_socket = SecureFileUploader(db_uri=app.config[constants.SQLALCHEMY_DATABASE_URI], session=app.config[constants.DB_SESSION])
    app.config[constants.EVENT_HANDLERS].register_listener(file_socket)
    file_socket.start_upload_server()

with app.app_context():
    app.logger.info('Start BirdsAnalyser')
    bird_analyser_socket = BirdVideoAnalyzer(_db_uri=app.config[constants.SQLALCHEMY_DATABASE_URI], session=app.config[constants.DB_SESSION])
    app.config[constants.EVENT_HANDLERS].register_listener(bird_analyser_socket)
    bird_analyser_socket.start_analyse_server()

db = DBHandler(app.config[constants.SQLALCHEMY_DATABASE_URI], app.config[constants.DB_SESSION])
if db.check_config_entry_exists(constants.SYSTEM, constants.KEY) and db.get_config_entry(constants.SYSTEM,
                                                                                         constants.KEY) != '':
    key = db.get_config_entry(constants.SYSTEM, constants.KEY)
else:
    key = Fernet.generate_key()
    db.create_update_config_entry(constants.SYSTEM, constants.KEY, key)
if app.config['SECRET_KEY'] == '':
    app.config['SECRET_KEY'] = Fernet.generate_key()
    db.create_update_config_entry(constants.SYSTEM, constants.KEY, key)
cipher = Fernet(key)


@app.route('/')
@app.route('/personas', methods=['GET', 'POST'])
def personas():
    global first_visit, date_leave, date_chick, name_bird, date_eggs
    _db = DBHandler(app.config[constants.SQLALCHEMY_DATABASE_URI], app.config[constants.DB_SESSION])
    if request.method == 'GET':
        name_bird = app.config[constants.NAME_BIRD]
        first_visit = app.config[constants.FIRST_VISIT]
        date_eggs = app.config[constants.DATE_EGG]
        date_chick = app.config[constants.DATE_CHICK]
        date_leave = app.config[constants.DATE_LEAVE]
        name_bird = app.config[constants.NAME_BIRD]

    elif request.method == 'POST':
        name_bird = request.form['name_bird']
        first_visit = request.form['first_visit']
        date_eggs = request.form['date_eggs']
        date_chick = request.form['date_chick']
        date_leave = request.form['date_leave']

        if name_bird is not None or name_bird != '':
            _db.create_update_config_entry(constants.NEST_CONFIG, constants.NAME_BIRD, name_bird)
        if first_visit is not None or first_visit != '':
            _db.create_update_config_entry(constants.NEST_CONFIG, constants.FIRST_VISIT, first_visit)
        if date_eggs is not None or date_eggs != '':
            _db.create_update_config_entry(constants.NEST_CONFIG, constants.DATE_EGG, date_eggs)
        if date_chick is not None or date_chick != '':
            _db.create_update_config_entry(constants.NEST_CONFIG, constants.DATE_CHICK, date_chick)
        if date_leave is not None or date_leave != '':
            _db.create_update_config_entry(constants.NEST_CONFIG, constants.DATE_LEAVE, date_leave)
    folder_personas = app.config[constants.FOLDER_PERSONAS] + '/personas' + '.' + str(
        app.config[constants.ENDING_PIC])
    pic_personas = str(
        pathlib.Path(folder_personas).relative_to(app.root_path))
    latest_file_time = ''
    video_folder = app.config[constants.FOLDER_VIDEOS]
    list_of_files = glob.glob(video_folder + '/*' + app.config[constants.VID_FORMAT])
    num_files_today = len(glob.glob(video_folder + '/*' + str(datetime.datetime.today().day) + str(
        format(datetime.datetime.today().month, '02')) + str(datetime.datetime.today().year) + '*' + app.config[
                                        constants.VID_FORMAT]))
    if len(list_of_files) > 0:
        latest_file = max(list_of_files, key=os.path.getctime)
        latest_file_time = time.strftime(constants.DATETIME_FORMATE_UI, time.localtime(os.stat(latest_file).st_ctime))
    return render_template("personas.html", num_visits_today=num_files_today, last_visit=latest_file_time,
                           pic_personas=pic_personas, first_visit=first_visit, date_eggs=date_eggs,
                           date_chick=date_chick, date_leave=date_leave, name_bird=name_bird)


def gen():
    global stream_active
    stream_active = True
    client_socket, payload_size = appl.get_streaming_socket()

    while stream_active:
        image = appl.get_streaming_image(client_socket, payload_size)
        if image is None:
            continue
        _draw_label(image, datetime.datetime.now().strftime(constants.DATETIME_FORMAT), (20, 20))

        encode_return_code, image_buffer = cv2.imencode('.' + str(app.config[constants.ENDING_PIC]), image)
        io_buf = io.BytesIO(image_buffer)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + io_buf.read() + b'\r\n')


# Livestream für die Website
@app.route('/stream')
def stream():
    app.logger.debug('streaming page requested')
    return render_template('streaming.html')


# Route zum Aufnehmen eines Videos direkt über die Website
@app.route('/capture_video')
def capture_video():
    # Define the codec and create VideoWriter object
    app.logger.debug('create video on user request')
    with app.app_context():
        appl.create_video()
    return redirect(url_for('stream'))


@app.route('/slide_show')
def slide_show():
    # Auslesen der Bilder im Applikationsverzeichnis und Anzeige auf der Webseite
    # die Konfiguration des Verzeichnisses erfolgt in der config.py
    app.logger.debug('slide show request received')
    pictures = []

    pic_path = app.config[constants.FOLDER_PICTURES]
    pictures_list = pathlib.Path(str(pic_path)).glob('*' + str(app.config[constants.ENDING_PIC]))
    for pic in pictures_list:
        pict = [pic.name, str(pic.relative_to(app.root_path))]
        pictures.append(pict)
    return render_template('pictures.html', pictures=pictures)


@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    app.logger.debug('request to stop stream received')
    global stream_active
    stream_active = False  # Signalisiert dem Generator, dass er stoppen soll
    return '', 200


def _draw_label(img, text, pos):
    # zeichnen des Labels in das Bild
    # die Position und der einzufügende Text werden als Parameter übergeben
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = .4
    color = (255, 255, 255)
    cv2.putText(img, text, pos, font_face, scale, color, 1, cv2.LINE_AA)


@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    app.logger.debug('streming page started')
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture_picture')
def capture_picture():
    file_name_short = app.config[constants.PREFIX_PIC] + datetime.datetime.now().strftime(
        app.config[constants.TIME_FORMAT_FILE]) + '.' + str(
        app.config[constants.ENDING_PIC])
    full_filename = os.path.join(app.config[constants.FOLDER_PICTURES], file_name_short)
    _take_picture(full_filename)
    app.logger.debug(f'picture with name {full_filename} created')
    return redirect(url_for('stream'))


# Aufnehmen eines Fotos
def _take_picture(fileName):
    client_socket, payload_size = appl.get_streaming_socket()
    image = appl.get_streaming_frame(client_socket, payload_size)

    if np.array(image).size > 1:
        _draw_label(image, datetime.datetime.now().strftime(constants.DATETIME_FORMAT), (20, 20))
        image_gray = image
        cv2.imwrite(fileName, image_gray)
        client_socket.close()


@app.route('/video_list_raw', methods=['GET', 'POST'])
def video_list_raw():
    videos = []
    vid_list = []
    app.logger.debug('video list page requested')
    if request.method == 'POST':
        form_datum = request.form.get('dateFiles')
        sel_datum = datetime.datetime.strptime(form_datum, constants.DATEFORMATE_FILE_SEL)
    else:
        sel_datum = datetime.datetime.today()

    vid_path = app.config[constants.FOLDER_VIDEOS]

    pattern = '*' + app.config[constants.VID_FORMAT]
    vid_list = pathlib.Path(str(vid_path)).glob(pattern)

    for media in vid_list:
        vid = [media.name, str(media.relative_to(app.root_path))]
        videos.append(vid)
    return render_template('video_list_raw.html', videos=videos, date_selection=sel_datum)


@app.route('/video_list_detect', methods=['GET', 'POST'])
def video_list_detect():
    videos = []
    vid_list = []
    app.logger.debug('video list page requested')
    if request.method == 'POST':
        form_datum = request.form.get('dateFiles')
        sel_datum = datetime.datetime.strptime(form_datum, constants.DATEFORMATE_FILE_SEL)
    else:
        sel_datum = datetime.datetime.today()

    vid_path = app.config[constants.FOLDER_VIDEOS_DETECT]

    pattern = '*' + app.config[constants.VID_FORMAT]
    vid_list = pathlib.Path(vid_path).glob(pattern)

    for media in vid_list:
        vid = [media.name, str(media.relative_to(app.root_path))]
        videos.append(vid)
    return render_template('video_list_detect.html', videos=videos, date_selection=sel_datum)


@app.route('/replay_list', methods=['GET', 'POST'])
def replay_list():
    videos = []
    vid_list = []
    app.logger.debug('replay page requested')
    if request.method == 'POST':
        form_datum = request.form.get('dateFiles')
        sel_datum = datetime.datetime.strptime(form_datum, constants.DATEFORMATE_FILE_SEL)
    else:
        sel_datum = datetime.datetime.today()

    vid_path = app.config[constants.FOLDER_REPLAY]
    pattern = app.config[constants.VID_FORMAT]
    vid_list= pathlib.Path(vid_path).glob(pattern)

    for media in vid_list:
        vid = [media.name, str(media.relative_to(app.root_path))]
        videos.append(vid)
    app.logger.debug(f'{len(videos)} found')
    return render_template('replays.html', videos=videos, date_selection=sel_datum)


@app.route('/video_list_no_detect', methods=['GET', 'POST'])
def video_list_no_detect():
    videos = []
    vid_list = []
    vid_path = app.config[constants.FOLDER_VIDEOS_NO_DETECT]
    sel_datum = None
    if request.method == 'POST':
        form_datum = request.form.get('dateFiles')
        sel_datum = datetime.datetime.strptime(form_datum, constants.DATEFORMATE_FILE_SEL)
    else:
        sel_datum = datetime.datetime.today()

    pattern = '*' + app.config[constants.VID_FORMAT]

    vid_list.extend(list(pathlib.Path(vid_path).glob(pattern)))

    for media in vid_list:
        vid = [media.name, str(media.relative_to(app.root_path))]
        videos.append(vid)
    return render_template('video_list_no_detect.html', videos=videos, date_selection=sel_datum)


def _clean_folder(folder, pattern):
    if os.path.exists(folder):
        for file_object in os.listdir(folder):
            file_object_path = os.path.join(folder, file_object)
            if file_object.startswith(pattern):
                if os.path.isfile(file_object_path) or os.path.islink(file_object_path):
                    os.unlink(file_object_path)
    else:
        os.makedirs(folder)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    admin_form = AdminForm()
    if request.method == 'POST':
        app_config = [
            [constants.DURATION_VID, 'duration_vid', 'int'],
            [constants.VID_RES_X, 'vid_res_x', 'int'],
            [constants.VID_RES_Y, 'vid_res_y', 'int'],
            [constants.SENSITIVITY, 'sensitivity', 'int'],
            [constants.PREFIX_VID, 'prefix_vid', 'str'],
            [constants.REPLAY_ENABLED, 'replay_enabled', 'bool'],
            [constants.REPLAY_INTERVAL, 'replay_interval', 'int'],
            [constants.FRAMES_PER_SEC_REPLAY, 'frames_per_sec_replay', 'int'],
            [constants.REPLAY_DAYS, 'replay_days', 'int'],
            [constants.GRAYSCALE_ENABLED, 'grayscale', 'bool'],

            [constants.SERVER_UPLOAD_ENABLED, 'upload_enabled', 'bool'],
            [constants.DELETE_AFTER_UPLOAD_ENABLED, 'delete_enabled', 'bool'],
            [constants.DELETE_NO_DETECT_ENABLED, 'delete_nodetect_enabled', 'bool'],
            [constants.KEEP_FILE_LOCAL, 'keep_file_time', 'int'],
            [constants.NUM_RETRY_UPLOAD, 'num_retry_upload', 'int'],
            [constants.PAUSE_RETRY_UPLOAD, 'pause_retry_upload', 'int'],

            [constants.SMB_SERVER, 'smb_host', 'str'],
            [constants.SMB_USER, 'smb_user', 'str'],
            [constants.SMB_PASSWORD, 'smb_password', 'str'],
            [constants.SMB_SHARE, 'smb_share', 'str'],

            [constants.NEXT_CLOUD_SERVER, 'nextcloud_url', 'str'],
            [constants.NEXT_CLOUD_USER, 'nextcloud_user', 'str'],
            [constants.NEXT_CLOUD_PASSWORD, 'nextcloud_password', 'str'],

            [constants.FTP_SERVER, 'ftp_url', 'str'],
            [constants.FTP_USER, 'ftp_user', 'str'],
            [constants.FTP_PASSWORD, 'ftp_password', 'str'],
            [constants.FTP_SHARE, 'ftp_share', 'str'],

            [constants.TIME_UPLOAD, 'time_upload', 'date'],
            [constants.ENDING_PIC, 'pic_ending', 'str'],
            [constants.PREFIX_PIC, 'prefix_pic', 'str'],

            [constants.VID_ANALYSER_TIME_RUN, 'time_vid_sorter', 'date'],
            [constants.VID_ANALYSER_ENABLED, 'vid_sorter_enabled', 'bool']
        ]

        for appConfigEntry in app_config:
            if admin_form.data.get("service") == 'smb':
                app.config[constants.SMB_ENABLED] = 1
                app.config[constants.FTP_ENABLED] = 0
                app.config[constants.NEXT_CLOUD_ENABLED] = 0
                app.config[constants.SMB_SERVER] = request.form.get('smb_host')
                app.config[constants.SMB_USER] = request.form.get('smb_user')
                app.config[constants.SMB_PASSWORD] = cipher.encrypt(request.form.get('smb_password').encode())
                app.config[constants.SMB_SHARE] = request.form.get('smb_share')
            if admin_form.data.get("service") == 'ftp':
                app.config[constants.SMB_ENABLED] = 0
                app.config[constants.FTP_ENABLED] = 1
                app.config[constants.NEXT_CLOUD_ENABLED] = 0
                app.config[constants.FTP_SERVER] = request.form.get('ftp_host')
                app.config[constants.FTP_PORT] = request.form.get('ftp_port')
                app.config[constants.FTP_USER] = request.form.get('ftp_user')
                app.config[constants.FTP_PASSWORD] = cipher.encrypt(request.form.get('ftp_password').encode())
                app.config[constants.FTP_SHARE] = request.form.get('ftp_share')
            if admin_form.data.get("service") == 'nextcloud':
                app.config[constants.SMB_ENABLED] = 0
                app.config[constants.FTP_ENABLED] = 0
                app.config[constants.NEXT_CLOUD_ENABLED] = 1
                app.config[constants.NEXT_CLOUD_SERVER] = request.form.get('nextcloud_url')
                app.config[constants.NEXT_CLOUD_USER] = request.form.get('nextcloud_user')
                app.config[constants.NEXT_CLOUD_PASSWORD] = cipher.encrypt(
                    request.form.get('nextcloud_password').encode())
                app.config[constants.NEXT_CLOUD_FOLDER] = request.form.get('nextcloud_share')
            if appConfigEntry[0][-8:] == '_ENABLED' and request.form.get(appConfigEntry[1]) is None:
                app.config[appConfigEntry[0]] = False
            elif appConfigEntry[0][-8:] == '_ENABLED' and request.form.get(appConfigEntry[1]) is not None:
                app.config[appConfigEntry[0]] = True

            else:
                if request.form.get(appConfigEntry[1]) is not None and appConfigEntry[2] != 'int':
                    app.config[appConfigEntry[0]] = request.form.get(appConfigEntry[1])
                elif request.form.get(appConfigEntry[1]) is not None and appConfigEntry[2] == 'int':
                    app.config[appConfigEntry[0]] = int(float(request.form.get(appConfigEntry[1])))
                else:
                    continue
        if not app.config[constants.REPLAY_ENABLED]:
            clear_path_screen_shots()
        update_setup(_app=app)
        app.config[constants.EVENT_HANDLERS].notify_listener(DatabaseChangeEvent)

    if app.config[constants.DURATION_VID] is None:
        admin_form.duration_vid.data = int(0)
        admin_form.duration_vidVal.data = int(0)
    else:
        admin_form.duration_vid.data = int(float(app.config[constants.DURATION_VID]))
        admin_form.duration_vidVal.data = int(float(app.config[constants.DURATION_VID]))
    if app.config[constants.VID_RES_X] is None:
        admin_form.vid_res_x.data = int(0)
    else:
        admin_form.vid_res_x.data = int(app.config[constants.VID_RES_X])
    if app.config[constants.VID_RES_Y] is None:
        admin_form.vid_res_y.data = int(0)
    else:
        admin_form.vid_res_y.data = int(app.config[constants.VID_RES_Y])
    if app.config[constants.SENSITIVITY] is None:
        admin_form.sensitivity.data = int(0)
        admin_form.sensitivityVal.data = int(0)
    else:
        admin_form.sensitivity.data = int(float(app.config[constants.SENSITIVITY]))
        admin_form.sensitivityVal.data = int(float(app.config[constants.SENSITIVITY]))
    if app.config[constants.REPLAY_INTERVAL] is None:
        admin_form.replay_interval.data = int(0)
    else:
        admin_form.replay_interval.data = int(app.config[constants.REPLAY_INTERVAL])
    if app.config[constants.REPLAY_DAYS] is None:
        admin_form.replay_days.data = int(0)
    else:
        admin_form.replay_days.data = int(app.config[constants.REPLAY_DAYS])
    if app.config[constants.FRAMES_PER_SEC_REPLAY] is None:
        admin_form.frames_per_sec_replay.data = int(0)
    else:
        admin_form.frames_per_sec_replay.data = int(app.config[constants.FRAMES_PER_SEC_REPLAY])
    if int(app.config[constants.FTP_ENABLED]) == 1:
        admin_form.service.data = 'ftp'
    if int(app.config[constants.SMB_ENABLED]) == 1:
        admin_form.service.data = 'smb'
    if int(app.config[constants.NEXT_CLOUD_ENABLED]) == 1:
        admin_form.service.data = 'nextcloud'

    admin_form.smb_host.data = app.config[constants.SMB_SERVER]
    admin_form.smb_user.data = app.config[constants.SMB_USER]
    admin_form.smb_password.data = app.config[constants.SMB_PASSWORD]
    admin_form.smb_password.render_kw = {"value": app.config[constants.SMB_PASSWORD]}
    admin_form.smb_share.data = app.config[constants.SMB_SHARE]

    admin_form.ftp_host.data = app.config[constants.FTP_SERVER]
    admin_form.ftp_user.data = app.config[constants.FTP_USER]
    admin_form.ftp_password.data = app.config[constants.FTP_PASSWORD]
    admin_form.ftp_share.data = app.config[constants.FTP_SHARE]
    admin_form.ftp_port.data = app.config[constants.FTP_PORT]

    admin_form.nextcloud_url.data = app.config[constants.NEXT_CLOUD_SERVER]
    admin_form.nextcloud_user.data = app.config[constants.NEXT_CLOUD_USER]
    admin_form.nextcloud_password.data = app.config[constants.NEXT_CLOUD_PASSWORD]
    admin_form.nextcloud_share.data = app.config[constants.NEXT_CLOUD_FOLDER]

    if app.config[constants.NUM_RETRY_UPLOAD] is None:
        admin_form.num_retry_upload.data = int(0)
    else:
        admin_form.num_retry_upload.data = int(app.config[constants.NUM_RETRY_UPLOAD])

    if app.config[constants.PAUSE_RETRY_UPLOAD] is None:
        admin_form.pause_retry_upload.data = int(0)
    else:
        admin_form.pause_retry_upload.data = int(app.config[constants.PAUSE_RETRY_UPLOAD])

    admin_form.prefix_vid.data = app.config[constants.PREFIX_VID]

    if app.config[constants.DELETE_AFTER_UPLOAD_ENABLED]:
        admin_form.delete_enabled.data = True
    else:
        admin_form.delete_enabled.data = False
    if app.config[constants.DELETE_NO_DETECT_ENABLED]:
        admin_form.delete_nodetect_enabled.data = True
    else:
        admin_form.delete_nodetect_enabled.data = False

    if int(app.config[constants.GRAYSCALE_ENABLED]) == 1:
        admin_form.grayscale.data = True
    else:
        admin_form.grayscale.data = False

    if app.config[constants.REPLAY_ENABLED]:
        admin_form.replay_enabled.data = True
    else:
        admin_form.replay_enabled.data = False

    if app.config[constants.SERVER_UPLOAD_ENABLED]:
        admin_form.upload_enabled.data = True
    else:
        admin_form.upload_enabled.data = False
    if app.config[constants.VID_ANALYSER_ENABLED]:
        admin_form.vid_sorter_enabled.data = True
    else:
        admin_form.vid_sorter_enabled.data = False
    admin_form.keep_file_time.data = app.config[constants.KEEP_FILE_LOCAL]
    admin_form.vid_sorter_frame_dist.data = app.config[constants.VID_ANALYSER_FRAME_DISTANCE]
    admin_form.time_upload.data = datetime.datetime.strptime(app.config[constants.TIME_UPLOAD],
                                                             constants.UPLOAD_TIME_FORMAT).time()
    admin_form.time_vid_sorter.data = datetime.datetime.strptime(app.config[constants.VID_ANALYSER_TIME_RUN],
                                                                 constants.UPLOAD_TIME_FORMAT).time()
    admin_form.prefix_pic.data = app.config[constants.PREFIX_PIC]
    admin_form.pic_ending.data = app.config[constants.ENDING_PIC]

    if admin_form.validate_on_submit():
        return redirect(url_for("admin"))
    return render_template(
        "admin_new.html",
        form=admin_form,
        template="form-template"
    )


def clear_path_screen_shots():
    screen_shots = []
    pattern = '*.' + app.config[constants.ENDING_PIC]
    screen_path = app.config[constants.FOLDER_REPLAY_SCREENSHOT]
    screen_shots.extend(list(sorted(pathlib.Path(screen_path).glob(pattern), key=os.path.getmtime,
                                    reverse=True)))
    for screen in screen_shots:
        os.remove(screen)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port='5000', debug=True, use_reloader=False)
