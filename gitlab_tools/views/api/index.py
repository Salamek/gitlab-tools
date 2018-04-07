# -*- coding: utf-8 -*-

from flask import jsonify, request

from gitlab_tools.blueprints import api_index
from gitlab_tools.tasks.gitlab_tools import sync_pull_mirror, sync_push_mirror
from gitlab_tools.models.gitlab_tools import PullMirror, PushMirror


__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@api_index.route('/pull/sync/<int:mirror_id>', methods=['POST'])
def schedule_sync_pull_mirror(mirror_id: int):
    hook_token = request.args.get('token')
    if not hook_token:
        return jsonify({'message': 'Token was not provided'}), 400

    found_mirror = PullMirror.query.filter_by(id=mirror_id).first()
    if not found_mirror:
        return jsonify({'message': 'Mirror not found'}), 404

    if found_mirror.hook_token != hook_token:
        return jsonify({'message': 'Provided token was incorrect'}), 400

    if not found_mirror.project_id:
        return jsonify({'message': 'Project mirror is not created, cannot be synced'}), 400

    task = sync_pull_mirror.delay(found_mirror.id)
    return jsonify({'message': 'Sync task started', 'uuid': task.id}), 200


@api_index.route('/push/sync/<int:mirror_id>', methods=['POST'])
def schedule_sync_push_mirror(mirror_id: int):
    hook_token = request.args.get('token')
    if not hook_token:
        return jsonify({'message': 'Token was not provided'}), 400

    found_mirror = PushMirror.query.filter_by(id=mirror_id).first()
    if not found_mirror:
        return jsonify({'message': 'Mirror not found'}), 404

    if found_mirror.hook_token != hook_token:
        return jsonify({'message': 'Provided token was incorrect'}), 400

    if not found_mirror.project_id:
        return jsonify({'message': 'Project mirror is not created, cannot be synced'}), 400

    task = sync_push_mirror.delay(found_mirror.id)
    return jsonify({'message': 'Sync task started', 'uuid': task.id}), 200