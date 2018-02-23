
# -*- coding: utf-8 -*-

import flask
import paramiko
import os
import datetime
import json
import hashlib
import base64
import urllib.parse
import dateutil.parser
from flask_login import current_user, login_required
from gitlab_tools.forms.fingerprint import NewForm
from gitlab_tools.tools.helpers import detect_vcs_protocol, \
    parse_scp_like_url, \
    get_user_public_key_path, \
    get_user_private_key_path, \
    get_user_know_hosts_path
from gitlab_tools.tools.formaters import format_md5_fingerprint, format_sha256_fingerprint
from gitlab_tools.tools.crypto import get_remote_server_key, calculate_fingerprint, import_key, sign_data, verify_data
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from gitlab_tools.blueprints import fingerprint_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


def check_fingerprint_hostname(hostname):
    """
    Helper function to check hostname fingerprint
    :param hostname: 
    :return: 
    """
    know_hosts_path = get_user_know_hosts_path(current_user, flask.current_app.config['USER'])

    host_keys = paramiko.hostkeys.HostKeys(know_hosts_path if os.path.isfile(know_hosts_path) else None)
    remote_server_key_lookup = host_keys.lookup(hostname)

    if remote_server_key_lookup:
        key_name, = remote_server_key_lookup
        remote_server_key = remote_server_key_lookup[key_name]
        found = True
    else:
        # Not found, request validation
        remote_server_key = get_remote_server_key(hostname)
        found = False

    data = {
        'found': found,
        'datetime': datetime.datetime.now().isoformat(),
        'hostname': hostname,
        'rsa_md5_fingerprint': format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5')),
        'rsa_sha256_fingerprint': format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
    }

    data_sign = json.dumps(data, sort_keys=True).encode()
    private_key = import_key(get_user_private_key_path(current_user, flask.current_app.config['USER']))
    data['signature'] = base64.b64encode(sign_data(data_sign, private_key))
    return flask.jsonify(data), 200


@fingerprint_index.route('/', methods=['GET'])
@login_required
def get_fingerprint():
    know_hosts_path = get_user_know_hosts_path(current_user, flask.current_app.config['USER'])
    host_keys = paramiko.hostkeys.HostKeys(know_hosts_path if os.path.isfile(know_hosts_path) else None)
    host_keys_proccessed = []
    for host_key in host_keys:
        keys = []
        for type in host_keys[host_key].keys():
            remote_server_key = host_keys[host_key][type]
            keys.append({
                'type': type,
                'md5_fingerprint': format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5')),
                'sha256_fingerprint': format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
            })

        host_keys_proccessed.append({
            'hostname': host_key,
            'keys': keys
        })

    return flask.render_template('fingerprint.index.fingerprint.html', host_keys_proccessed=host_keys_proccessed)


@fingerprint_index.route('/new', methods=['GET', 'POST'])
@login_required
def new_fingerprint():
    form = NewForm(
        flask.request.form
    )
    if flask.request.method == 'POST' and form.validate():
        # If we get here, it means JS check was not triggered for some reason, maybe JS disabled ?
        flask.flash('You need to have JavaScript enabled for this.', 'danger')
        return flask.redirect(flask.url_for('fingerprint.index.get_fingerprint'))

    return flask.render_template('fingerprint.index.new.html', form=form)


@fingerprint_index.route('/delete/<string:hostname>', methods=['GET'])
@login_required
def delete_fingerprint(hostname: str):
    know_hosts_path = get_user_know_hosts_path(current_user, flask.current_app.config['USER'])
    host_keys = paramiko.hostkeys.HostKeys(know_hosts_path if os.path.isfile(know_hosts_path) else None)
    # !FIXME i could not find a better way how to do this
    for entry in host_keys._entries:
        if hostname in entry.hostnames:
            host_keys._entries.remove(entry)

    host_keys.save(know_hosts_path)
    flask.flash('Fingerprint was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('fingerprint.index.get_fingerprint'))


@fingerprint_index.route('/fingerprint-check', methods=['POST'])
@login_required
def check_hostname_fingerprint():
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

    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.hostname:
        hostname = str(parsed_url.hostname)
    else:
        hostname = url

    return check_fingerprint_hostname(hostname)


@fingerprint_index.route('/fingerprint-check-vcs', methods=['POST'])
@login_required
def check_vcs_hostname_fingerprint():
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

    if detect_vcs_protocol(url) == ProtocolEnum.SSH:
        parsed_url = urllib.parse.urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            parsed_url = parse_scp_like_url(url)
            hostname = parsed_url['hostname']
        hostname_string = str(hostname)
        return check_fingerprint_hostname(hostname_string)


@fingerprint_index.route('/fingerprint-add', methods=['POST'])
@login_required
def add_hostname_fingerprint():
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

    remote_server_key = get_remote_server_key(hostname)

    data = {
        'found': json_data.get('found'),
        'datetime': json_data.get('datetime'),
        'hostname': hostname,
        # Recalculation fingerprint for remote_server_key and not using one in resuest
        # ensures that fingerprint did not change (signature chech would fail)
        'rsa_md5_fingerprint': format_md5_fingerprint(calculate_fingerprint(remote_server_key, 'md5')),
        'rsa_sha256_fingerprint': format_sha256_fingerprint(calculate_fingerprint(remote_server_key, 'sha256'))
    }
    data_sign = json.dumps(data, sort_keys=True).encode()
    # Validate signature
    public_key = import_key(get_user_public_key_path(current_user, flask.current_app.config['USER']))
    signature = base64.b64decode(flask.request.json.get('signature'))
    if not verify_data(data_sign, signature, public_key):
        # Déjà vu, It happens when they change something...
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
    know_hosts_path = get_user_know_hosts_path(current_user, flask.current_app.config['USER'])
    host_keys = paramiko.hostkeys.HostKeys(know_hosts_path if os.path.isfile(know_hosts_path) else None)
    host_keys.add(data['hostname'], remote_server_key.get_name(), remote_server_key)
    host_keys.save(know_hosts_path)

    return flask.jsonify({
        'message': 'OK'
    }), 200



