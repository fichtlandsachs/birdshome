from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    BooleanField,
    SubmitField,
    SelectField,
    RadioField

)
from wtforms.fields import (
    TimeField,
    IntegerField,
    DecimalRangeField,
    PasswordField
)
from wtforms.validators import (
    DataRequired,
    URL
)


class AdminForm(FlaskForm):
    style = {'class': 'adminFormOutputField', 'disabled': 'disabled"', 'style': 'border:0'}
    """Admin Bereich für Nistkasten"""
    duration_vid = DecimalRangeField(label='Dauer der Videoaufnahme in s', validators=[DataRequired()],
                                     default=Decimal(15))
    duration_vidVal = IntegerField(label='', render_kw=style)
    grayscale = BooleanField(label='Bild in Graustufen')
    vid_res_x = IntegerField(label='Video X', render_kw=style)
    vid_res_y = IntegerField(label='Video Y', render_kw=style)
    sensitivity = DecimalRangeField(label='Empflindlichkeit', default=Decimal(10))
    sensitivityVal = IntegerField(label='', render_kw=style)
    prefix_vid = StringField(label='Videoprefix',
                             validators=[DataRequired(message="Please enter a prefix for the video naming.")])
    pic_ending = SelectField(label='Endung der Bilder', validators=[DataRequired()],
                             choices=[
                                 ('jpg', '.jpg')
                             ]
                             )
    replay_enabled = BooleanField(label='automatische Aufnahmen')
    replay_interval = IntegerField(label='Intervall Einzelbilder in Minuten')
    replay_days = IntegerField(label='Zeitraum für Zeitraffer')
    frames_per_sec_replay = IntegerField(label='Bilder je sec Zeitraffer')
    upload_enabled = BooleanField(label='Serverupload', render_kw={"onchange": "toggleServerUpload()"})

    radio_server_upload = RadioField(
        choices=[('ftp_upload', 'FTP'), ('folder_upload', 'eingebundenes Verzeichnis'),
                 ('next_cloud_upload', 'NextCloud'), ('smb_upload', 'Samba-Laufwerk')]
    )
    service = RadioField(label='Dienst', choices=[('smb', 'SMB'), ('nextcloud', 'Nextcloud'), ('ftp', 'FTP')],
                         default='smb')
    # Eingabefelder für SMB
    smb_share = StringField(label='SMB Share', validators=[DataRequired()])
    smb_host = StringField(label='SMB Host', validators=[DataRequired()])
    smb_user = StringField(label='SMB Benutzername', validators=[DataRequired()])
    smb_password = PasswordField(label='SMB Passwort', validators=[DataRequired()])
    # Eingabefelder für Nextcloud
    nextcloud_url = StringField(label='Nextcloud URL', validators=[DataRequired()])
    nextcloud_share = StringField(label='Nextcloud Share', validators=[DataRequired()])
    nextcloud_user = StringField(label='Nextcloud Benutzername', validators=[DataRequired()])
    nextcloud_password = PasswordField(label='Nextcloud Passwort', validators=[DataRequired()])
    # Eingabefelder für FTP
    ftp_host = StringField(label='FTP Host', validators=[DataRequired()])
    ftp_port = StringField(label='FTP Port', validators=[DataRequired()])
    ftp_share = StringField(label='FTP Share', validators=[DataRequired()])
    ftp_user = StringField(label='FTP Benutzername', validators=[DataRequired()])
    ftp_password = PasswordField(label='FTP Passwort', validators=[DataRequired()])

    delete_enabled = BooleanField(label='Dateien nach Upload lokal löschen')
    keep_file_time = IntegerField(label='Dateien noch für x Tage lokal halten')
    delete_nodetect_enabled = BooleanField(label='Videos ohne Tiere direkt löschen (Beta)')
    pause_retry_upload = IntegerField(label='Warten bei Nichterreichbarkeit in Minuten')
    num_retry_upload = IntegerField(label='Anzahl Versuche Upload')
    time_upload = TimeField(label='Zeitpunkt')
    # Zusatzeinstellungen zum Upload
    vid_sorter_enabled = BooleanField(label='Videosortierer')
    time_vid_sorter = TimeField(label='Zeitpunkt für Videosortierung')
    vid_sorter_frame_dist = IntegerField(label='Frameabstand')

    # Einstellungen für den Zeitraffer
    prefix_pic = StringField(label='Prefix für Bilder')

    website = StringField(
        'Website',
        validators=[URL()]
    )
    submit = SubmitField(label='Speichern')
