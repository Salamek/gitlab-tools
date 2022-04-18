
# -*- coding: utf-8 -*-

import flask
import os
import datetime
import urllib.parse
import gitlab
import requests
from flask_login import login_user, logout_user, login_required

from gitlab_tools.blueprints import sign_index
from gitlab_tools.tasks.gitlab_tools import create_rsa_pair
from gitlab_tools.tools.crypto import random_password
from gitlab_tools.extensions import db
from gitlab_tools.models.gitlab_tools import User, OAuth2State


__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@sign_index.route('/in', methods=['GET'])
def login():
    return flask.render_template('sign.index.login.html')


@sign_index.route('/in/request', methods=['GET'])
def request_login():
    state = random_password()

    new_oauth_state = OAuth2State()
    new_oauth_state.state = state

    db.session.add(new_oauth_state)

    redirect_url = '{}?{}'.format(
        os.path.join(flask.current_app.config['GITLAB_URL'], 'oauth', 'authorize'),
        urllib.parse.urlencode({
            'client_id': flask.current_app.config['GITLAB_APP_ID'],
            'redirect_uri': flask.url_for('sign_index.do_login', _external=True),
            'response_type': 'code',
            'state': state
        })
    )
    db.session.commit()
    return flask.redirect(redirect_url)


@sign_index.route('/in/do', methods=['GET'])
def do_login():
    state = flask.request.args.get('state')
    code = flask.request.args.get('code')

    if not state or not code:
        flask.abort(400)

    # Lets find out if we issued that state, and if so, delete it to prevent replay

    found_oauth_state = OAuth2State.query.filter_by(state=state).first_or_404()
    db.session.delete(found_oauth_state)
    db.session.commit()  # We need to commit right now
    try:
        # Lets get token info from API
        oauth_url = os.path.join(flask.current_app.config['GITLAB_URL'], 'oauth', 'token')
        r = requests.post(
            oauth_url,
            {
                'client_id': flask.current_app.config['GITLAB_APP_ID'],
                'client_secret': flask.current_app.config['GITLAB_APP_SECRET'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': flask.url_for('sign_index.do_login', _external=True)
            }
        )
        r.raise_for_status()
        response_data = r.json()

        # Lets fetch current user info
        gl = gitlab.Gitlab(
            flask.current_app.config['GITLAB_URL'],
            oauth_token=response_data['access_token'],
            api_version=flask.current_app.config['GITLAB_API_VERSION']
        )

        gl.auth()

        logged_user = gl.user

        found_user = User.query.filter_by(gitlab_id=logged_user.id).first()
        if not found_user:
            found_user = User()
            found_user.gitlab_id = logged_user.id
            found_user.is_rsa_pair_set = False
        found_user.name = logged_user.name
        found_user.avatar_url = logged_user.avatar_url
        found_user.access_token = response_data['access_token']
        found_user.refresh_token = response_data['refresh_token']
        found_user.created = datetime.datetime.fromtimestamp(response_data['created_at'])

        db.session.add(found_user)
        db.session.commit()

        if not found_user.is_rsa_pair_set:
            create_rsa_pair.delay(found_user.id)

        login_user(found_user, remember=True)
        flask.flash('You has been logged in successfully', 'success')
        return flask.redirect(flask.url_for('home_index.get_home'))
    except requests.exceptions.HTTPError as e:
        db.session.rollback()
        flask.flash('Login failed: {}'.format(str(e)), 'danger')
        flask.abort(500)


@sign_index.route("/out")
@login_required
def logout():
    logout_user()
    return flask.redirect(flask.url_for('sign_index.login'))
