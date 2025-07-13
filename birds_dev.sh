#!/bin/bash
source /etc/venv/birdshome/bin/activate
export FLASK_ENV=production
export ENV=development
gunicorn --bind 0.0.0.0:5000 --threads 5 -w 1 --timeout 120 app:app
