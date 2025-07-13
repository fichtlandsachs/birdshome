# Birdshome
watch birds nest

The project is based on a raspberry pi 4 with 4GB RAM

using a raspberry cam and a microphone it enables you to stream the camera an produces small movies based on opencv including pyaudio soud sequences 

New version of the project birdshome. 

Featurelist:
- live stream to the nesting box
- automtatic video creation
- automatic replay creation
- automatic video sorter based on yolo
- automatic upload to samba share or sftp server
- admin page to configure system behavior
- samba share for direct access to the videos, replays and photos

The video stream is now located in a video socket an all processes connect via http to this socket.

Installation sequence:

sudo apt-get install -y build-essential libcap-dev libssl-dev zlib1g-dev libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev tk-dev libffi-dev wget samba gunicorn nginx sqlite3 libffi-dev libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good ffmpeg libopencv-dev libhdf5-dev libatlas-base-dev portaudio19-dev software-properties-common ufw  libopenblas-dev
sudo apt-get install -y python3-opencv
sudo apt-get install -y python3-libcamera
sudo apt-get install -y python3-flask-sqlalchemy
sudo apt-get install -y python3-flask*
sudo apt install python3-paramiko
sudo mkdir /etc/birdshome
sudo chown pi:pi /etc/birdshome
sudo mkdir /etc/venv
sudo mkdir /etc/venv/birdshome
sudo chown pi:pi -R /etc/venv
sudo apt autoremove

python3 -m venv --system-site-packages /etc/venv/birdshome
source /etc/venv/birdshome/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install picamera2

check the following settings on your raspberry pi

sudo nano /boot/firmware/config.txt
Them following entries must be set:

camera_auto_detect=1

dtoverlay=vc4-kms-v3d


copy the project to /etc/birdshome

make the bash file executable

chmod +x birds_dev.sh


set the password for the samba user and enable the user for samba access

sudo smbpasswd -a <user>

sudo smbpasswd -e <user>

update /etc/samba/smb.conf and add the following entries, you can use the user and group pi for standard access

[bird_media]
path = /etc/birdshome/application/static/media
public = yes
writable = yes
comment = video share
printable = no
guest ok = no
valid users = <user>, @<group>
write list = <user>, @<group>

create a service to startup the server automatically on system startup

sudo nano /etc/systemd/system/birdshome.service

[Unit]
Description=birdshome Service
After=network.target

[Service]
Type=simple
User=<user>
WorkingDirectory=/etc/birdshome
Restart=always
ExecStart=/etc/birdshome/birds_dev.sh


[Install]
WantedBy=multi-user.target

start the service
sudo systemctl enable birdshome.service
sudo systemctl start birdshome

to use nginx as a reverse proxy generate the following files

sudo nano /etc/nginx/sites-available/birdshome

server {
    listen 80;
    server_name <systemname>;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

sudo ln -s /etc/nginx/sites-available/birdshome /etc/nginx/sites-enabled/

sudo nginx -t

sudo systemctl reload nginx

update the firewall setting to restrict the access

sudo ufw allow 'Nginx Full'

sudo ufw allow 22

sudo ufw allow 80

sudo ufw allow 445

sudo ufw enable

if now enter http://<systemname> you will access the webpage of the server