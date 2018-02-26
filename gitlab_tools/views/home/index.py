import flask
import os
import paramiko
from flask_login import current_user, login_required
from gitlab_tools.models.gitlab_tools import PullMirror
from gitlab_tools.tools.helpers import get_user_public_key_path, get_user_private_key_path
from gitlab_tools.tools.formaters import format_md5_fingerprint, format_sha256_fingerprint
from gitlab_tools.tools.crypto import import_key, calculate_fingerprint
from gitlab_tools.blueprints import home_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@home_index.route('/', methods=['GET'])
@login_required
def get_home():
    pull_mirrors = PullMirror.query.count()
    private_key_path = get_user_private_key_path(current_user, flask.current_app.config['USER'])
    if os.path.isfile(private_key_path):

        with open(private_key_path, 'r') as f:
            private_key = paramiko.RSAKey.from_private_key(f)
        fingerprint_md5 = format_md5_fingerprint(calculate_fingerprint(private_key, 'md5'))
        fingerprint_sha256 = format_sha256_fingerprint(calculate_fingerprint(private_key, 'sha256'))
    else:
        private_key = None
        fingerprint_md5 = None
        fingerprint_sha256 = None

    return flask.render_template(
        'home.index.home.html',
        pull_mirrors=pull_mirrors,
        private_key=private_key,
        fingerprint_md5=fingerprint_md5,
        fingerprint_sha256=fingerprint_sha256
    )
