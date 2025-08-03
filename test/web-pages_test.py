import pytest


@pytest.fixture(scope="session")
def client():
    from app import app
    with app.test_client() as c:
        yield c

def test_index_page(client, page):
    rv = client.get('/')
    assert rv.status_code == 200
    page.goto('https://localhost/')
    assert 'Birdshome' in page.title()
    assert b'<html' in rv.data  # Template enthält HTML

    validate_menu(rv=rv)

def test_personas_page(client):
    rv = client.get('/personas')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_stream_page(client):
    rv = client.get('/stream')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_capture_video_page(client):
    rv = client.get('/capture_video')
    assert rv.status_code == 302
    assert b'<html' in rv.data

def test_slide_show_page(client):
    rv = client.get('/slide_show')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_capture_picture_page(client):
    rv = client.get('/capture_picture')
    assert rv.status_code == 302
    assert b'<html' in rv.data

def test_video_list_raw_page(client):
    rv = client.get('/video_list_raw')
    assert rv.status_code == 200
    assert b'video' in rv.data.lower()
    validate_menu(rv=rv)

def test_video_list_detect_page(client):
    rv = client.get('/video_list_detect')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_video_list_no_detect_page(client):
    rv = client.get('/video_list_no_detect')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_admin_page(client):
    rv = client.get('/admin')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_replay_list_page(client):
    rv = client.get('/replay_list')
    assert rv.status_code == 200
    assert b'<html' in rv.data
    validate_menu(rv=rv)

def test_stop_stream(client):
    rv = client.post('/stop_stream')
    assert rv.status_code == 200
    assert rv.data == b''


def validate_menu(rv):
    html_page = str(rv.data).replace('\\n', '')
    assert 'id="we_live_here">Hier wohnen wir</a>' in html_page
    assert '<a href="capture_picture" id="cam">Foto aufnehmen</a>' in html_page
    assert '<a href="capture_video" id="record">Film aufnehmen</a>' in html_page
    assert '<a href="slide_show">Bilder</a>' in html_page
    assert '<a href="video_list_raw">Video neu</a>' in html_page
    assert '<a href="video_list_detect">Video</a>' in html_page
    assert '<a href="video_list_no_detect">Videos aussortiert</a>' in html_page
    assert '<a href="replay_list">Zeitraffer</a>' in html_page
    assert '<a href="admin" id="admin">Admin</a>' in html_page

def test_homepage_title(page):
    page.goto("https://localhost/")
    assert "Birdshome" in page.title()