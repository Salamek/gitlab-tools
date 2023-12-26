# -*- coding: utf-8 -*-

"""Flask and other extensions instantiated here.

To avoid circular imports with views and create_app(), extensions are instantiated here. They will be initialized
(calling init_app()) in application.py.
"""
import os
from logging import getLogger
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from flask_celery import Celery
from flask_login import LoginManager
from flask_migrate import Migrate
import gitlab_tools as app_root

LOG = getLogger(__name__)
APP_ROOT_FOLDER = os.path.abspath(os.path.dirname(app_root.__file__))
MIGRATE_ROOT_FOLDER = os.path.abspath(os.path.join(APP_ROOT_FOLDER, 'migrations'))


db = SQLAlchemy()
babel = Babel()
login_manager = LoginManager()
celery = Celery()
migrate = Migrate(directory=MIGRATE_ROOT_FOLDER)
