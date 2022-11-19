# -*- coding: utf-8 -*-
import socket
import os
from typing import Tuple
import datetime
import json
import base64
import dateutil.parser
import flask
import paramiko
from flask_login import current_user, login_required
from gitlab_tools.extensions import db
from gitlab_tools.forms.fingerprint import NewForm
from gitlab_tools.models.gitlab_tools import Fingerprint
from gitlab_tools.tools.helpers import get_user_public_key_path, \
    get_user_private_key_path, \
    get_user_known_hosts_path
from gitlab_tools.tools.formaters import format_md5_fingerprint, format_sha256_fingerprint
from gitlab_tools.tools.crypto import calculate_fingerprint, import_key, sign_data, verify_data
from gitlab_tools.tools.fingerprint import check_hostname, add_hostname, get_remote_server_key_for_hostname
from gitlab_tools.blueprints import fingerprint_index
from gitlab_tools.tools.GitUri import GitUri
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


def check_fingerprint_hostname(hostname: str) -> Tuple[flask.Response, int]:
    """
    Helper function to check hostname fingerprint
    :param hostname: string
    :return: (flask.Response, int)
    """
    known_hosts_path = get_user_known_hosts_path(current_user, flask.current_app.config['USER'])
    try:
        found, remote_server_key = check_hostname(hostname, known_hosts_path)
    except (TimeoutError, socket.timeout) as e:
        return flask.jsonify({
            'message': 'Failed to obtain SSH response with error: {}. (Is SSH server running at {} ?)'.format(str(e), hostname)
        }), 400

    data = {
        'found': found,
        'datetime': datetime.datetime.now().isoformat(),
        'hostname': hostname,
        'md5_fingerprint': format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5')),
        'sha256_fingerprint': format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
    }

    data_sign = json.dumps(data, sort_keys=True).encode()
    private_key = import_key(get_user_private_key_path(current_user, flask.current_app.config['USER']))
    data['signature'] = base64.b64encode(sign_data(data_sign, private_key)).decode("ascii")
    return flask.jsonify(data), 200


@fingerprint_index.route('/', methods=['GET'])
@login_required
def get_fingerprint() -> Tuple[flask.Response, int]:
    known_hosts_path = get_user_known_hosts_path(current_user, flask.current_app.config['USER'])
    host_keys = paramiko.hostkeys.HostKeys(known_hosts_path if os.path.isfile(known_hosts_path) else None)
    host_keys_processed = []
    for host_key in host_keys:

        keys = []
        sha256_fingerprints = []
        for key_type in host_keys[host_key].keys():
            remote_server_key = host_keys[host_key][key_type]
            sha256_fingerprint = format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
            sha256_fingerprints.append(sha256_fingerprint)
            md5_fingerprint = format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5'))
            keys.append({
                'type': key_type,
                'md5_fingerprint': md5_fingerprint,
                'sha256_fingerprint': sha256_fingerprint
            })

        fingerprint_info = Fingerprint.query.filter(Fingerprint.user_id == current_user.id,
                                                    Fingerprint.hashed_hostname == host_key).first()

        if not fingerprint_info:
            fingerprint_info = Fingerprint.query.filter(Fingerprint.user_id == current_user.id,
                                                        Fingerprint.sha256_fingerprint.in_(sha256_fingerprints)).first()

        color_class = 'danger'
        title = '{} - Not in fingerprint database'.format(host_key)
        if fingerprint_info:
            if fingerprint_info.hashed_hostname == host_key:
                color_class = 'success'
                title = '{} - Matched by hostname hash'.format(host_key)
            else:
                color_class = 'warning'
                title = '{} - Matched by hostname fingerprint'.format(host_key)

        host_keys_processed.append({
            'hostname': fingerprint_info.hostname if fingerprint_info else host_key,
            'title': title,
            'color_class': color_class,
            'hashed_hostname': host_key,
            'keys': keys
        })

    return flask.Response(
        flask.render_template('fingerprint.index.fingerprint.html', host_keys_proccessed=host_keys_processed)
    ), 200


@fingerprint_index.route('/new', methods=['GET', 'POST'])
@login_required
def new_fingerprint() -> Tuple[flask.Response, int]:
    form = NewForm(
        flask.request.form
    )
    if flask.request.method == 'POST' and form.validate():
        flask.flash('New fingerprint was added.', 'success')
        return flask.redirect(flask.url_for('fingerprint_index.get_fingerprint')), 302

    return flask.Response(
        flask.render_template('fingerprint.index.new.html', form=form)
    ), 200


@fingerprint_index.route('/delete/<path:hostname>', methods=['GET'])
@login_required
def delete_fingerprint(hostname: str) -> flask.Response:
    known_hosts_path = get_user_known_hosts_path(current_user, flask.current_app.config['USER'])
    host_keys = paramiko.hostkeys.HostKeys(known_hosts_path if os.path.isfile(known_hosts_path) else None)
    # !FIXME i could not find a better way how to do this
    for entry in host_keys._entries:
        if hostname in entry.hostnames:
            host_keys._entries.remove(entry)

    host_keys.save(known_hosts_path)
    flask.flash('Fingerprint was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('fingerprint_index.get_fingerprint'))


@fingerprint_index.route('/fingerprint-check', methods=['POST'])
@login_required
def check_hostname_fingerprint() -> Tuple[flask.Response, int]:
    json_data = flask.request.get_json()
    if not json_data:
        return flask.jsonify({
            'message': 'No data'
        }), 400

    url = json_data.get('url')
    if not url:
        return flask.jsonify({
            'message': 'Required parameter URL is missing'
        }), 400

    parsed_url = GitUri(url)
    if parsed_url.protocol == ProtocolEnum.SSH:
        # Fingerprint check should be initiated only for SSH protocol
        if parsed_url.port != parsed_url.default_port:
            hostname = '[{}]:{}'.format(parsed_url.hostname, parsed_url.port)
        else:
            hostname = parsed_url.hostname
        return check_fingerprint_hostname(hostname)

    # For everything else we will return "found" to skip all fingerprint stuff
    return flask.jsonify({'found': True}), 200


@fingerprint_index.route('/fingerprint-add', methods=['POST'])
@login_required
def add_hostname_fingerprint() -> Tuple[flask.Response, int]:
    json_data = flask.request.get_json()
    if not json_data:
        return flask.jsonify({
            'message': 'No data'
        }), 400

    hostname = json_data.get('hostname')
    if not hostname:
        return flask.jsonify({
            'message': 'Required parameter hostname is missing'
        }), 400

    remote_server_key = get_remote_server_key_for_hostname(hostname)

    data = {
        'found': json_data.get('found'),
        'datetime': json_data.get('datetime'),
        'hostname': hostname,
        # Recalculation fingerprint for remote_server_key and not using one in request
        # ensures that fingerprint did not change (signature check would fail)
        'md5_fingerprint': format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5')),
        'sha256_fingerprint': format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
    }
    data_sign = json.dumps(data, sort_keys=True).encode()
    # Validate signature
    public_key = import_key(get_user_public_key_path(current_user, flask.current_app.config['USER']))
    signature = base64.b64decode(flask.request.json.get('signature'))
    if not verify_data(data_sign, signature, public_key):
        # Déjà vu Neo, It happens when they change something...
        return flask.jsonify({
            'message': 'Signature is invalid, we will get out of this hotel!'
        }), 401

    # We got here, signature is valid, lets check time
    # Check date, allow only 2h old signatures
    from_date = datetime.datetime.today() - datetime.timedelta(hours=2)
    if dateutil.parser.parse(data['datetime']) < from_date:
        return flask.jsonify({
            'message': 'Signature is older than 2 hours, please generate a new one'
        }), 403

    # Everything looks "hunky dory" lets continue
    known_hosts_path = get_user_known_hosts_path(current_user, flask.current_app.config['USER'])

    found = check_hostname(hostname, known_hosts_path)[0]
    if found:
        return flask.jsonify({
            'message': 'Fingerprint is already in known_hosts file'
        }), 200

    hashed_hostname = add_hostname(data['hostname'], remote_server_key, known_hosts_path)

    found_fingerprint = Fingerprint.query.filter_by(hashed_hostname=hashed_hostname, user_id=current_user.id).first()
    if not found_fingerprint:
        found_fingerprint = Fingerprint()
        found_fingerprint.hostname = data['hostname']
        found_fingerprint.user_id = current_user.id
        found_fingerprint.hashed_hostname = hashed_hostname
        found_fingerprint.sha256_fingerprint = data['sha256_fingerprint']
        db.session.add(found_fingerprint)
        db.session.commit()

    return flask.jsonify({
        'message': 'OK',
        'hashed_hostname': hashed_hostname
    }), 200
