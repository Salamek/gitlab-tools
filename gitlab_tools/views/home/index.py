import os
from typing import Tuple
import flask
import paramiko
from flask_login import current_user, login_required
from gitlab_tools.extensions import db
from gitlab_tools.models.gitlab_tools import PullMirror, PushMirror, Fingerprint
from gitlab_tools.tasks.gitlab_tools import create_rsa_pair
from gitlab_tools.tools.helpers import get_user_private_key_path
from gitlab_tools.tools.formaters import format_md5_fingerprint, format_sha256_fingerprint
from gitlab_tools.tools.crypto import calculate_fingerprint
from gitlab_tools.blueprints import home_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@home_index.route('/', methods=['GET'])
@login_required
def get_home() -> Tuple[str, int]:
    pull_mirrors_count = PullMirror.query.filter_by(is_deleted=False, user=current_user).count()
    push_mirrors_count = PushMirror.query.filter_by(is_deleted=False, user=current_user).count()
    fingerprint_count = Fingerprint.query.filter_by(user=current_user).count()
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
        pull_mirrors_count=pull_mirrors_count,
        push_mirrors_count=push_mirrors_count,
        fingerprint_count=fingerprint_count,
        private_key=private_key,
        fingerprint_md5=fingerprint_md5,
        fingerprint_sha256=fingerprint_sha256
    ), 200


@home_index.route('/new-rsa-key', methods=['GET'])
def get_new_rsa_key() -> flask.Response:

    current_user.is_rsa_pair_set = False  # pylint: disable=assigning-non-slot
    current_user.gitlab_deploy_key_id = None  # pylint: disable=assigning-non-slot
    db.session.add(current_user)
    db.session.commit()

    create_rsa_pair.delay(current_user.id)
    flask.flash('New RSA pair key has been requested!', 'success')
    return flask.redirect(flask.url_for('home_index.get_home'))
