import logging
import os
import socket
import threading
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from time import sleep

import paramiko
import requests
from cryptography.fernet import Fernet
from smb.SMBConnection import SMBConnection

import constants
from application.handler.database_hndl import DBHandler, DatabaseChangeEvent


class SecureFileUploader:
    def __init__(self, db_uri, retries=3, delay=5):
        """
        Initialisiert den Uploader mit der Anzahl der Wiederholungsversuche und der Wartezeit (in Sekunden)
        """
        self.logger = logging.getLogger('SecureFileUploaderLogger')
        self.logger.setLevel(logging.DEBUG)
        log_file = '/etc/birdshome/application/log/SecureFileUploader.log'
        logger_handler = RotatingFileHandler(filename=log_file, maxBytes=100000, backupCount=10)
        logger_handler.setLevel(logging.DEBUG)
        # Format für die Log-Meldungen definieren
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger_handler.setFormatter(formatter)
        # Handler dem Logger hinzufügen
        self.logger.addHandler(logger_handler)
        self._retries = retries
        self._delay = delay
        self._dbHandler = DBHandler(db_uri)

        self._server_not_found = False
        self._server_upload_enabled = 0
        self._ftp_enabled = 0
        self._smb_enabled = 0
        self._nextcloud_enabled = 0
        self._key = ''
        self._delete_after_upload = 0
        self._video_folder = ''
        self._server = ''
        self._share = ''
        self._user_upload = ''
        self._user_password = ''
        self._keep_file_time = 0
        self._upload = False
        self.ip_adress = '0.0.0.0'
        self.server_not_found = False
        self._update_config()

    def handle_database_event(self, event: DatabaseChangeEvent):
        self._update_config()

    def _update_config(self):
        self._server_upload_enabled = int(
            self._dbHandler.get_config_entry(constants.SMB, constants.SERVER_UPLOAD_ENABLED))
        self._smb_enabled = int(self._dbHandler.get_config_entry(constants.SMB, constants.SMB_ENABLED))
        self._next_cloud_enabled = int(
            self._dbHandler.get_config_entry(constants.NEXT_CLOUD, constants.NEXT_CLOUD_ENABLED))
        self._ftp_enabled = int(self._dbHandler.get_config_entry(constants.FTP, constants.FTP_ENABLED))
        if self._server_upload_enabled == 1:
            if self._ftp_enabled == 1:
                self._smb_enabled = 0
                self._nextcloud_enabled = 0
                self._server = self._dbHandler.get_config_entry(constants.FTP, constants.FTP_SERVER)
                self._user_upload = self._dbHandler.get_config_entry(constants.FTP, constants.FTP_USER)
                self._user_password = self._dbHandler.get_config_entry(constants.FTP, constants.FTP_PASSWORD)
                self._port = int(self._dbHandler.get_config_entry(constants.FTP, constants.FTP_PORT))
                self._share = self._dbHandler.get_config_entry(constants.FTP, constants.FTP_SHARE)
            if self._smb_enabled == 1:
                self._ftp_enabled = 0
                self._nextcloud_enabled = 0
                self._server = self._dbHandler.get_config_entry(constants.SMB, constants.SMB_SERVER)
                self._user_upload = self._dbHandler.get_config_entry(constants.SMB, constants.SMB_USER)
                self._user_password = self._dbHandler.get_config_entry(constants.SMB, constants.SMB_PASSWORD)
                self._share = self._dbHandler.get_config_entry(constants.SMB, constants.SMB_SHARE)
            if self._next_cloud_enabled == 1:
                self._ftp_enabled = 0
                self._smb_enabled = 0
                self._server = self._dbHandler.get_config_entry(constants.NEXT_CLOUD, constants.NEXT_CLOUD_SERVER)
                self._user_upload = self._dbHandler.get_config_entry(constants.NEXT_CLOUD, constants.NEXT_CLOUD_USER)
                self._user_password = self._dbHandler.get_config_entry(constants.NEXT_CLOUD,
                                                                       constants.NEXT_CLOUD_PASSWORD)
                self._share = self._dbHandler.get_config_entry(constants.NEXT_CLOUD, constants.NEXT_CLOUD_FOLDER)

        self._time_upload = self._dbHandler.get_config_entry(constants.SMB, constants.TIME_UPLOAD)
        self._keep_file_time = self._dbHandler.get_config_entry(constants.SMB, constants.KEEP_FILE_LOCAL)
        self._key = self._dbHandler.get_config_entry(constants.SYSTEM, constants.KEY)
        self._delete_after_upload = self._dbHandler.get_config_entry(constants.SMB,
                                                                     constants.DELETE_AFTER_UPLOAD_ENABLED)
        if self._delete_after_upload is None:
            self._delete_after_upload = 0
        else:
            self._delete_after_upload = int(self._delete_after_upload)
        self._video_format = self._dbHandler.get_config_entry(constants.VIDEO, constants.VID_FORMAT)
        self._video_folder = self._dbHandler.get_config_entry(constants.VIDEO, constants.FOLDER_VIDEOS)
        self._replay_folder = self._dbHandler.get_config_entry(constants.REPLAY, constants.FOLDER_REPLAY)
        self._picture_folder = self._dbHandler.get_config_entry(constants.SYSTEM, constants.FOLDER_PICTURES)

    def upload(self):
        while True:
            self._upload = False
            if int(self._server_upload_enabled) == 1:
                time_upload = self._time_upload.split(':')
                time_now = datetime.now().time()

                if time_now.hour >= int(time_upload[0]) or time_now.hour < 3:
                    self.logger.info('Start uploading files')
                    self.upload_folder(self._picture_folder)
                    self.upload_folder(self._video_folder)
                    self.upload_folder(self._replay_folder)
            sleep(self._delay * 60)

    def upload_folder(self, path):
        delete_local = False
        if self._delete_after_upload == 1:
            delete_local = True
        paths = str(path).split('/')
        folder_upload = paths[len(paths) - 1]
        self.logger.info(f'Start uploading files from folder {path}')
        self.upload_files(path, folder_upload, delete_local)

    def start_upload_server(self):
        threading.Thread(target=self.upload).start()

    def upload_files(self, folder_local: str, folder_remote: str, delete_local=False):
        if self._key == '':
            self.logger.info('Cancel uploading files due to missing key')
        if self._smb_enabled == 1:
            self.logger.info(f'Using smb for upload')
            smb_passw = Fernet(self._key).decrypt(self._user_password).decode()
            self.upload_samba(retries=self._retries, delay=self._delay, server_name=self._server,
                              username=self._user_upload,
                              password=smb_passw,
                              share_name=os.path.join(self._share, folder_remote),
                              folder=folder_remote,
                              local_files=folder_local,
                              delete_local=delete_local)
        elif self._next_cloud_enabled == 1:
            self.logger.info(f'Using nextcloud for upload')
            nextcloud_passw = Fernet(self._key).decrypt(self._user_password).decode()
            self.upload_nextcloud(retries=self._retries, delay=self._delay, base_url=self._server,
                                  username=self._user_upload,
                                  password=nextcloud_passw,
                                  remote_path=os.path.join(self._share, folder_remote),
                                  local_files=folder_local)
        elif self._ftp_enabled == 1:
            self.logger.info(f'Using ftp for upload')
            sftp_password = Fernet(self._key).decrypt(self._user_password).decode()
            self.upload_directory_sftp(retries=self._retries, delay=self._delay, host=self._server, port=self._port,
                                       username=self._user_upload,
                                       password=sftp_password, local_folder=folder_local,
                                       remote_path=os.path.join(self._share, folder_remote))

    def check_network(self):
        try:
            self.ip_adress = socket.gethostbyname(self._server)
            self.server_not_found = False
            return self.ip_adress
        except Exception as e:
            self.server_not_found = True
            self.logger.error(f'Can not find server {self._server}')

    def upload_samba(self, retries, delay, server_name, username, password, share_name, folder, local_files,
                     delete_local=False):
        """
        Upload auf einen Samba-Share mit einem einfachen Resume-Mechanismus.
        """
        for attempt in range(retries):
            try:
                conn = SMBConnection(username, password, 'client', server_name, domain='WORKGROUP', use_ntlm_v2=True)
                server_ip = socket.gethostbyname(server_name)
                conn.connect(server_ip, 139)

                for file in local_files:
                    # Versuche, die Größe der bereits vorhandenen Datei zu ermitteln
                    remote_file_size = 0
                    remote_file = os.path.join(share_name, folder, file.name)
                    try:
                        file_list = conn.listPath(service_name=share_name, path=os.path.join(share_name, folder))
                        for f in file_list:
                            if f.filename == file.name:
                                remote_file_size = f.file_size
                                break
                    except Exception:
                        remote_file_size = 0

                    local_file_size = os.path.getsize(file)
                    if remote_file_size == local_file_size:
                        if delete_local:
                            os.remove(file)
                        # conn.close()
                    else:
                        with open(file, 'rb') as file_obj:
                            # Zum Resume: Wir setzen den Dateizeiger auf den bereits hochgeladenen Offset
                            file_obj.seek(remote_file_size)
                            # Achtung: pysmbs storeFile unterstützt keinen Append-Modus – hier müsste evtl. eine eigene Blockübertragung implementiert werden.
                            conn.storeFile(service_name=share_name, path=remote_file, file_obj=file_obj)
                conn.close()
                return True
            except Exception as e:
                self.logger.error(f"Samba Upload Versuch {attempt + 1} fehlgeschlagen: {e}")
                sleep(delay)
        return False

    def upload_nextcloud(self, retries, delay, base_url, username, password, local_files, remote_path):
        """
        Upload zu Nextcloud (über WebDAV) mit einfachem Resume-Ansatz.
        Hinweis: Standard-HTTP PUT unterstützt normalerweise keinen Append-Modus. Für
        eine echte Resume-Funktion müssten ggf. serverseitige Erweiterungen genutzt werden.
        """
        url = f"{base_url}{remote_path}"
        for attempt in range(retries):
            for file in local_files:
                try:
                    # Ermitteln der remote-Dateigröße mittels HEAD-Request
                    head_resp = requests.request("HEAD", url, auth=(username, password))
                    if head_resp.status_code == 200 and 'Content-Length' in head_resp.headers:
                        remote_file_size = int(head_resp.headers.get('Content-Length', 0))
                    else:
                        remote_file_size = 0

                    local_file_size = os.path.getsize(file)
                    if remote_file_size >= local_file_size:
                        self.logger.info(f'File {file} already uploaded')
                        return True

                    with open(file, 'rb') as file_obj:
                        # file_obj.seek(remote_file_size)
                        # Achtung: Der folgende PUT-Request überschreibt in der Regel die gesamte Datei.
                        response = requests.put(url, data=file_obj, auth=(username, password))
                    if response.status_code in (200, 201, 204):
                        return True
                    else:
                        self.logger.error(f"Nextcloud Upload Fehlermeldung {response.status_code}: {response.text}")
                except Exception as e:
                    self.logger.error(f"Nextcloud Upload Versuch {attempt + 1} fehlgeschlagen: {e}")
                sleep(delay)
        return False

    def upload_directory_sftp(self, retries, delay, host, port, username, password, local_folder, remote_path):
        """
        Kopiert rekursiv das Verzeichnis local_dir (inkl. Unterverzeichnisse) per SFTP auf den Server.
        Dabei wird vor dem Upload jedes Verzeichnisses geprüft, ob es auf der Remote-Seite existiert;
        falls nicht, wird es erstellt.
        """
        global remote_folder, sftp, transport
        self.check_network()
        if self.server_not_found:
            self.logger.error(f"Verbindung zu Server {self._server} fehlgeschlagen")
            return
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            home_folder = sftp.normalize('.')
            # Sicherstellen, dass der Uploadpfadeinstieg auch verfügbar ist
            paths = str(remote_path).split('/')
            for remote_folder in paths:
                try:
                    sftp.chdir(remote_folder)
                except Exception as e:
                    sftp.mkdir(remote_folder)
                    sftp.chdir(remote_folder)
            # jetzt rekursiv die Dateien und Verzeichnisse erzeugen
            if self._delete_after_upload == 0:
                delete_local = False
            else:
                delete_local = True
            self.upload_files(_sftp=sftp, folder_local=local_folder, folder_remote=remote_folder,
                              delete_local=delete_local)


        except Exception as e:
            print(e)
        finally:
            sftp.close()
            transport.close()
        sftp.close()
        transport.close()
        return True

    def upload_files(self, _sftp, folder_local, folder_remote, delete_local=False):
        curr_folder = _sftp.normalize('.')
        _sftp.chdir(curr_folder)
        with os.scandir(folder_local) as entries:
            for entry in entries:
                if entry.is_dir():
                    try:
                        _sftp.chdir(entry.name)
                    except Exception as e:
                        _sftp.mkdir(entry.name)
                        _sftp.chdir(entry.name)
                    folder_remote_lcl = os.path.join(folder_remote, entry.name)
                    folder_local_lcl = os.path.join(folder_local, entry.name)
                    self.upload_files(_sftp=_sftp, folder_local=folder_local_lcl, folder_remote=folder_remote_lcl,
                                      delete_local=delete_local)
                    _sftp.chdir(curr_folder)
                if entry.is_file():
                    self.upload_file(_sftp=_sftp, file_name=entry.name, local_path=folder_local,
                                     delete_local=delete_local)

    def upload_file(self, _sftp, file_name, local_path, delete_local=False):
        global local_file
        curr_folder = _sftp.normalize('.')
        try:

            local_file = str(os.path.join(os.path.join(local_path, file_name)))
            # Resume-Logik
            try:
                remote_size = _sftp.stat(file_name).st_size
            except IOError:
                remote_size = 0
            local_size = os.path.getsize(local_file)
            if remote_size >= local_size:
                self.logger.info(f"{local_file} bereits vollständig hochgeladen.")
                return
            with open(local_file, 'rb') as f:
                time_file = os.path.getctime(f)
                createion_date = datetime.fromtimestamp(time_file)
                if remote_size:
                    f.seek(remote_size)
                    mode = 'ab'
                else:
                    mode = 'wb'
                with _sftp.open(file_name, mode) as remote_f:
                    while True:
                        data = f.read(32768)
                        if not data:
                            break
                        remote_f.write(data)
            self.logger.info(f"{local_file} erfolgreich hochgeladen nach {file_name}.")

            if self._delete_after_upload == 1:
                if datetime.now() - createion_date < timedelta(days=self._keep_file_time):
                    os.remove(file_name)
        except Exception as e:
            self.logger.error(f"Fehler beim Upload von {local_file}: {e}")
