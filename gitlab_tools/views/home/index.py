import flask
import os

from flask_login import current_user, login_required
from gitlab_tools.models.gitlab_tools import PullMirror
from gitlab_tools.tools.helpers import get_user_public_key_path
from gitlab_tools.blueprints import home_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@home_index.route('/', methods=['GET'])
@login_required
def get_home():
    mirrors = PullMirror.query.count()
    public_key_path = get_user_public_key_path(current_user, flask.current_app.config['USER'])
    if os.path.isfile(public_key_path):
        with open(public_key_path, 'r') as f:
            public_key = f.read()
    else:
        public_key = 'Not yet generated...'
    return flask.render_template('home.index.home.html', mirrors=mirrors, public_key=public_key)
