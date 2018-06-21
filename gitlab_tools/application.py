# -*- coding: utf-8 -*-

import decimal
import os
from importlib import import_module

import flask.json
from flask import Flask, url_for, request
from flask_babel import gettext
from gitlab_tools.blueprints import all_blueprints
from gitlab_tools.config import Config
from yaml import load

import gitlab_tools as app_root
from gitlab_tools.extensions import db, sentry, babel, login_manager, navigation, migrate, celery

APP_ROOT_FOLDER = os.path.abspath(os.path.dirname(app_root.__file__))
TEMPLATE_FOLDER = os.path.join(APP_ROOT_FOLDER, 'templates')
STATIC_FOLDER = os.path.join(APP_ROOT_FOLDER, 'static')
REDIS_SCRIPTS_FOLDER = os.path.join(APP_ROOT_FOLDER, 'redis_scripts')


def get_config(config_class_string: str, yaml_files: list=None) -> Config:
    """Load the Flask config from a class.
    Positional arguments:
    config_class_string -- string representation of a configuration class that will be loaded (e.g.
        'gitlab-tools.config.Production').
    yaml_files -- List of YAML files to load. This is for testing, leave None in dev/production.
    Returns:
    A class object to be fed into app.config.from_object().
    """
    config_module, config_class = config_class_string.rsplit('.', 1)
    config_obj = getattr(import_module(config_module), config_class)

    # Expand some options.
    db_fmt = 'gitlab_tools.models.{}'
    celery_fmt = 'gitlab_tools.tasks.{}'
    if getattr(config_obj, 'CELERY_IMPORTS', False):
        config_obj.CELERY_IMPORTS = [celery_fmt.format(m) for m in config_obj.CELERY_IMPORTS]
    for definition in getattr(config_obj, 'CELERYBEAT_SCHEDULE', dict()).values():
        definition.update(task=celery_fmt.format(definition['task']))
    if getattr(config_obj, 'DB_MODELS_IMPORTS', False):
        config_obj.DB_MODELS_IMPORTS = [db_fmt.format(m) for m in config_obj.DB_MODELS_IMPORTS]

    # Load additional configuration settings.
    yaml_files = yaml_files or [f for f in [
        os.path.join('/', 'etc', 'gitlab-tools', 'config.yml'),
        os.path.abspath(os.path.join(APP_ROOT_FOLDER, '..', 'config.yml')),
        os.path.join(APP_ROOT_FOLDER, 'config.yml'),
    ] if os.path.exists(f)]
    additional_dict = dict()
    for y in yaml_files:
        with open(y) as f:
            loaded_data = load(f.read())
            if isinstance(loaded_data, dict):
                additional_dict.update(loaded_data)
            else:
                raise Exception('Failed to parse configuration {}'.format(y))

    # Merge the rest into the Flask app config.
    for key, value in additional_dict.items():
        setattr(config_obj, key, value)

    return config_obj


def create_app(config_obj: Config, no_sql: bool=False) -> Flask:

    """Create an application."""
    app = Flask(__name__, template_folder=TEMPLATE_FOLDER, static_folder=STATIC_FOLDER)
    config_dict = dict([(k, getattr(config_obj, k)) for k in dir(config_obj) if not k.startswith('_')])
    app.config.update(config_dict)

    # Import DB models. Flask-SQLAlchemy doesn't do this automatically like Celery does.
    with app.app_context():
        for model in app.config.get('DB_MODELS_IMPORTS', list()):
            import_module(model)

    for bp in all_blueprints:
        import_module(bp.import_name)
        app.register_blueprint(bp)

    class FloatJSONEncoder(flask.json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, decimal.Decimal):
                # Convert decimal instances to float.
                return float(obj)
            return super(FloatJSONEncoder, self).default(obj)

    app.json_encoder = FloatJSONEncoder

    def url_for_other_page(page: int):
        args = request.view_args.copy()
        args['page'] = page
        return url_for(request.endpoint, **args)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page

    if not no_sql:
        db.init_app(app)

    migrate.init_app(app, db)
    sentry.init_app(app)
    babel.init_app(app)
    navigation.init_app(app)
    celery.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = "sign.index.login"
    login_manager.login_message_category = "info"
    login_manager.localize_callback = gettext

    login_manager.refresh_view = "sign.index.login"
    login_manager.needs_refresh_message = (
        u"To protect your account, please reauthenticate to access this page."
    )
    login_manager.needs_refresh_message_category = "info"

    app.sentry = sentry

    with app.app_context():
        import_module('gitlab_tools.middleware')

    return app
