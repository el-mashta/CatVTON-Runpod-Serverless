# gunicorn_conf.py
# This file contains the configuration for the Gunicorn server.

import os

# --- Server Socket ---
# Bind the server to this host and port.
bind = "0.0.0.0:8000"

# --- Worker Configuration ---
# The number of worker processes for handling requests.
workers = int(os.environ.get('GUNICORN_WORKERS', '3'))
worker_class = "uvicorn.workers.UvicornWorker"

# --- Logging ---
loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info')
accesslog = "-"
errorlog = "-"

# --- Process Management ---
# The file to which the Gunicorn master process ID will be written.
pidfile = os.environ.get('GUNICORN_PIDFILE', '/tmp/backend.pid')
# Run the master process in the background.
daemon = True
