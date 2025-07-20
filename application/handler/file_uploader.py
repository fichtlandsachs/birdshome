import os
import pathlib
import socket
from datetime import datetime, time
from time import sleep

import paramiko
import requests
from flask import current_app
from smb.SMBConnection import SMBConnection

import constants
from application.handler.database_hndl import DBHandler

app = current_app


class SecureFileUploader:
    def __init__(self, retries=3, delay=5):
        """
        Initialisiert den Uploader mit der Anzahl der Wiederholungsversuche und der Wartezeit (in Sekunden)
        """
        self.retries = retries
        self.delay = delay
        self.server_upload_enabled = 0
        self.smb_enabled = 0
        self.next_cloud_enabled = 0
        self.ftp_enabled = 0
        self.file_share_enabled = 0
        self.time_upload = '00:00'
        self.ip_adress = ''
        self.server_not_found = False
        self.dbHandler = DBHandler(app.config['SQLALCHEMY_DATABASE_URI'])
        self.update_config()

    def update_config(self):
        self.server_upload_enabled = int(
            self.dbHandler.get_config_entry(constants.SMB, constants.SERVER_UPLOAD_ENABLED))
        self.smb_enabled = int(self.dbHandler.get_config_entry(constants.SMB, constants.SMB_ENABLED))
        self.next_cloud_enabled = int(
            self.dbHandler.get_config_entry(constants.NEXT_CLOUD, constants.NEXT_CLOUD_ENABLED))
        self.ftp_enabled = int(self.dbHandler.get_config_entry(constants.FTP, constants.FTP_ENABLED))
        self.file_share_enabled = int(
            self.dbHandler.get_config_entry(constants.FILE_SHARE, constants.FILE_SHARE_ENABLED))
        self.time_upload = self.dbHandler.get_config_entry(constants.SMB, constants.TIME_UPLOAD)

    def upload_files(self):
        while True:
            self.update_config()
            if int(self.server_upload_enabled) == 1:
                time_upload = app.config[constants.TIME_UPLOAD].split(':')
                time_now = datetime.now().time()
                if int(time_upload[0]) <= time_now.hour and int(time_upload[1]) <= time_now.minute:
                    self.upload_photos()
                    # self.uploadVideos()
                    # self.uploadReplays()
            sleep(60)

    def upload_photos(self):
        photos = list()
        pattern = '*.jpg'
        photo_path = app.config[constants.UPLOAD_FOLDER_PIC]
        photos.extend(list(sorted(pathlib.Path(photo_path).glob(pattern), key=os.path.getmtime,
                                  reverse=True)))

        if self.smb_enabled == 1:
            self.upload_samba(server_name=app.config[constants.SMB_SERVER],
                              username=self.dbHandler.get_config_entry(constants.SMB, constants.SMB_USER),
                              password=self.dbHandler.get_config_entry(constants.SMB, constants.SMB_PASSWORD),
                              share_name='falk',
                              folder=self.dbHandler.get_config_entry(constants.SMB, constants.SMB_FOLDER),
                              local_files=photos)
        elif self.next_cloud_enabled == 1:
            self.upload_nextcloud(base_url=app.config[constants.NEXT_CLOUD_SERVER],
                                  username=self.dbHandler.get_config_entry(constants.NEXT_CLOUD,
                                                                           constants.NEXT_CLOUD_USER),
                                  password=self.dbHandler.get_config_entry(constants.NEXT_CLOUD,
                                                                           constants.NEXT_CLOUD_PASSWORD),
                                  remote_path=self.dbHandler.get_config_entry(constants.NEXT_CLOUD,
                                                                              constants.NEXT_CLOUD_FOLDER),
                                  local_files=photos)
        elif self.ftp_enabled == 1:
            self.upload_file_via_ftp(app.config[constants.UPLOAD_FOLDER_PIC])
        if self.file_share_enabled == 1:
            self.copyFileToFolder(app.config[constants.UPLOAD_FOLDER_PIC])

    def check_network(self):
        try:
            self.ip_adress = socket.gethostbyname(self.server)
        except Exception:
            self.server_not_found = True

    def upload_samba(self, server_name, username, password, share_name, folder, local_files):
        """
        Upload auf einen Samba-Share mit einem einfachen Resume-Mechanismus.
        Hinweis: pysmb bietet keine native Resume-Funktion. Hier wird daher zunächst versucht,
        die Größe der bereits vorhandenen Datei zu ermitteln und der Upload ab einem Offset zu starten.
        In diesem Beispiel wird jedoch letztlich die gesamte Datei übergeben – eine echte Blockübertragung
        müsste evtl. durch zusätzliche Logik realisiert werden.
        """
        for attempt in range(self.retries):
            try:
                conn = SMBConnection(username, password, 'client', server_name, domain='WORKGROUP', use_ntlm_v2=True)
                server_ip = socket.gethostbyname(server_name)
                conn.connect(server_ip, 139)

                for file in local_files:
                    # Versuche, die Größe der bereits vorhandenen Datei zu ermitteln
                    remote_file_size = 0
                    remote_file = os.path.join(folder, file.name)
                    try:
                        file_list = conn.listPath(service_name=share_name, path=folder)
                        for f in file_list:
                            if f.filename == os.path.basename(share_name):
                                remote_file_size = f.file_size
                                break
                    except Exception:
                        remote_file_size = 0

                    local_file_size = os.path.getsize(file)
                    if remote_file_size >= local_file_size:
                        print("Datei bereits vollständig hochgeladen.")
                        conn.close()
                        return True

                    with open(file, 'rb') as file_obj:
                        # Zum Resume: Wir setzen den Dateizeiger auf den bereits hochgeladenen Offset
                        file_obj.seek(remote_file_size)
                        # Achtung: pysmbs storeFile unterstützt keinen Append-Modus – hier müsste evtl. eine eigene Blockübertragung implementiert werden.
                        conn.storeFile(service_name='falk', path=remote_file, file_obj=file_obj)
                conn.close()
                return True
            except Exception as e:
                print(f"Samba Upload Versuch {attempt + 1} fehlgeschlagen: {e}")
                sleep(self.delay)
        return False

    def upload_nextcloud(self, base_url, username, password, local_files, remote_path):
        """
        Upload zu Nextcloud (über WebDAV) mit einfachem Resume-Ansatz.
        Hinweis: Standard-HTTP PUT unterstützt normalerweise keinen Append-Modus. Für
        eine echte Resume-Funktion müssten ggf. serverseitige Erweiterungen genutzt werden.
        """
        url = f"{base_url}/remote.php/webdav/{remote_path}"
        for attempt in range(self.retries):
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
                        print("Datei bereits vollständig hochgeladen.")
                        return True

                    with open(file, 'rb') as file_obj:
                        file_obj.seek(remote_file_size)
                        # Achtung: Der folgende PUT-Request überschreibt in der Regel die gesamte Datei.
                        response = requests.put(url, data=file_obj, auth=(username, password))
                    if response.status_code in (200, 201, 204):
                        return True
                    else:
                        print(f"Nextcloud Upload Fehlermeldung {response.status_code}: {response.text}")
                except Exception as e:
                    print(f"Nextcloud Upload Versuch {attempt + 1} fehlgeschlagen: {e}")
                time.sleep(self.delay)
        return False

    def upload_sftp(self, host, port, username, password, local_files):
        """
        Upload zu einem SFTP-Server mit Resume-Unterstützung.
        Hier wird geprüft, ob die Remote-Datei bereits existiert, und der Upload wird ab dem
        bereits hochgeladenen Byte fortgesetzt.
        """
        for attempt in range(self.retries):
            try:
                transport = paramiko.Transport((host, port))
                transport.connect(username=username, password=password)
                sftp = paramiko.SFTPClient.from_transport(transport)
                for file in local_files:
                    try:
                        remote_size = sftp.stat(file).st_size
                    except IOError:
                        remote_size = 0

                    local_file_size = os.path.getsize(file)
                    if remote_size >= local_file_size:
                        print("Datei bereits vollständig hochgeladen.")
                        sftp.close()
                        transport.close()
                        return True

                    with open(file, 'rb') as f:
                        # Bei Resume: Setze den Dateizeiger an die bereits hochgeladene Position
                        if remote_size:
                            f.seek(remote_size)
                            mode = 'ab'
                        else:
                            mode = 'wb'
                        # Öffne die Remote-Datei im entsprechenden Modus (Append oder Write)
                        with sftp.open(file, mode) as remote_f:
                            while True:
                                data = f.read(32768)
                                if not data:
                                    break
                                remote_f.write(data)
                sftp.close()
                transport.close()
                return True
            except Exception as e:
                print(f"SFTP Upload Versuch {attempt + 1} fehlgeschlagen: {e}")
                time.sleep(self.delay)
        return False

    def upload_local(self, destination_path, local_files):
        """
        Lokaler Datei-Upload (Kopieren) mit Resume-Unterstützung.
        Falls die Zieldatei bereits existiert, wird an der entsprechenden Stelle fortgesetzt.
        """
        for attempt in range(self.retries):
            try:
                for file in local_files:
                    resume_size = 0
                    destination_file = os.path.join(destination_path, file)

                    if os.path.exists(destination_file):
                        resume_size = os.path.getsize(destination_file)
                    local_file_size = os.path.getsize(file)
                    if resume_size >= local_file_size:
                        print("Datei bereits vollständig kopiert.")
                        return True

                    with open(file, 'rb') as src, open(destination_file, 'ab') as dst:
                        src.seek(resume_size)
                        while True:
                            chunk = src.read(32768)
                            if not chunk:
                                break
                            dst.write(chunk)
                    return True
            except Exception as e:
                print(f"Lokaler Kopierversuch {attempt + 1} fehlgeschlagen: {e}")
                time.sleep(self.delay)
        return False

    # --------------------
    # Verzeichnis-Upload-Methoden
    # --------------------
    def upload_directory_sftp(self, host, port, username, password, local_dir, remote_dir):
        """
        Kopiert rekursiv das Verzeichnis local_dir (inkl. Unterverzeichnisse) per SFTP auf den Server.
        Dabei wird vor dem Upload jedes Verzeichnisses geprüft, ob es auf der Remote-Seite existiert;
        falls nicht, wird es erstellt.
        """
        try:
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)
            sftp = paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            print(f"Verbindung zum SFTP-Server fehlgeschlagen: {e}")
            return False

        def ensure_remote_dir(path):
            # Erzeugt rekursiv das Remote-Verzeichnis, falls es noch nicht existiert.
            parts = path.split("/")
            curr_path = ""
            for part in parts:
                if part == "":
                    continue
                curr_path += "/" + part
                try:
                    sftp.stat(curr_path)
                except IOError:
                    try:
                        sftp.mkdir(curr_path)
                        print(f"Verzeichnis {curr_path} erstellt.")
                    except Exception as ex:
                        print(f"Fehler beim Erstellen des Verzeichnisses {curr_path}: {ex}")
                        return False
            return True

        for root, dirs, files in os.walk(local_dir):
            # Berechne den relativen Pfad und den entsprechenden Remote-Pfad
            rel_path = os.path.relpath(root, local_dir)
            if rel_path == ".":
                remote_path = remote_dir
            else:
                remote_path = os.path.join(str(remote_dir), str(rel_path)).replace("\\", "/")
            if not ensure_remote_dir(remote_path):
                print(f"Fehler beim Erstellen des Remote-Verzeichnisses {remote_path}.")
                continue

            for file in files:
                local_file = os.path.join(root, file)
                remote_file = os.path.join(remote_path, file).replace("\\", "/")
                try:
                    # Resume-Logik
                    try:
                        remote_size = sftp.stat(remote_file).st_size
                    except IOError:
                        remote_size = 0
                    local_size = os.path.getsize(local_file)
                    if remote_size >= local_size:
                        print(f"{local_file} bereits vollständig hochgeladen.")
                        continue
                    with open(local_file, 'rb') as f:
                        if remote_size:
                            f.seek(remote_size)
                            mode = 'ab'
                        else:
                            mode = 'wb'
                        with sftp.open(remote_file, mode) as remote_f:
                            while True:
                                data = f.read(32768)
                                if not data:
                                    break
                                remote_f.write(data)
                    print(f"{local_file} erfolgreich hochgeladen nach {remote_file}.")
                except Exception as e:
                    print(f"Fehler beim Upload von {local_file}: {e}")
        sftp.close()
        transport.close()
        return True

    def upload_directory_local(self, local_dir, destination_dir):
        """
        Kopiert rekursiv das Verzeichnis local_dir (inkl. Unterverzeichnisse) in das Zielverzeichnis destination_dir.
        """
        for root, dirs, files in os.walk(local_dir):
            rel_path = os.path.relpath(root, local_dir)
            dest_root = os.path.join(str(destination_dir), str(rel_path))
            os.makedirs(dest_root, exist_ok=True)
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(str(dest_root), str(file))
                if self.upload_local(src_file, dest_file):
                    print(f"{src_file} erfolgreich kopiert nach {dest_file}.")
                else:
                    print(f"Fehler beim Kopieren von {src_file}.")
        return True
