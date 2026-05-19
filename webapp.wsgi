"""
webapp.wsgi — Apache mod_wsgi entry point.

Apache's WSGIDaemonProcess does not source /etc/environment or the ec2-user
shell profile, so we load the .env file explicitly here (or rely on the
WSGIPassAuthorization / SetEnv directives in the VirtualHost block).
"""
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, '/var/www/webapp')

# Load .env if present (ignored safely if the file doesn't exist)
try:
    from dotenv import load_dotenv
    load_dotenv('/var/www/webapp/.env')
except ImportError:
    pass  # python-dotenv not installed; rely on SetEnv in Apache config

from app import app, init_database

# Initialise DB tables on first worker start
init_database()

application = app          # mod_wsgi looks for a callable named 'application'
