import logging
import socket
from flask import Flask
import sys
import os
import routes
from config import application
from config import dbManager
from config import config
from werkzeug.middleware.profiler import ProfilerMiddleware

config.configure_app(application)
dbManager.connect(application)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# application.wsgi_app = ProfilerMiddleware(
#     application.wsgi_app, restrictions=[30])

if __name__ == "__main__":
    application.run()
