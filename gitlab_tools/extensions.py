# -*- coding: utf-8 -*-

"""Flask and other extensions instantiated here.

To avoid circular imports with views and create_app(), extensions are instantiated here. They will be initialized
(calling init_app()) in application.py.
"""
import os
from logging import getLogger
import gitlab_tools as app_root
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from sqlalchemy.pool import Pool
from raven.contrib.flask import Sentry
from flask_babel import Babel
from flask_celery import Celery
from flask_redis import Redis
from flask_login import LoginManager
from flask_navigation import Navigation
from flask_migrate import Migrate
from flask_caching import Cache

LOG = getLogger(__name__)
APP_ROOT_FOLDER = os.path.abspath(os.path.dirname(app_root.__file__))
MIGRATE_ROOT_FOLDER = os.path.abspath(os.path.join(APP_ROOT_FOLDER, 'migrations'))


@listens_for(Pool, 'connect', named=True)
def _on_connect(dbapi_connection, **_) -> None:
    """Set MySQL mode to TRADITIONAL on databases that don't set this automatically.

    Without this, MySQL will silently insert invalid values in the database, causing very long debugging sessions in the
    long run.
    http://www.enricozini.org/2012/tips/sa-sqlmode-traditional/
    """
    pass
    # !FIXME set this only when MYSQL database is used
    # LOG.debug('FIXME! Setting SQL Mode to TRADITIONAL.')
    # dbapi_connection.cursor().execute("SET SESSION sql_mode='TRADITIONAL'")


db = SQLAlchemy()
sentry = Sentry()
babel = Babel()
login_manager = LoginManager()
navigation = Navigation()
celery = Celery()
redis = Redis()
migrate = Migrate(directory=MIGRATE_ROOT_FOLDER)
cache = Cache()
