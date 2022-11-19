# -*- coding: utf-8 -*-
from typing import Tuple
import flask
from flask import jsonify, request, url_for
from flask_login import login_required
from gitlab_tools.blueprints import api_index
from gitlab_tools.tasks.gitlab_tools import sync_pull_mirror, sync_push_mirror
from gitlab_tools.models.gitlab_tools import PullMirror, PushMirror
from gitlab_tools.models.celery import TaskMeta
from gitlab_tools.enums.InvokedByEnum import InvokedByEnum
from gitlab_tools.tools.gitlab import get_group, get_project, get_gitlab_instance
from gitlab_tools.tools.celery import log_task_pending


__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@api_index.route('/pull/sync/<int:mirror_id>', methods=['POST', 'GET'])
def schedule_sync_pull_mirror(mirror_id: int) -> Tuple[flask.Response, int]:
    hook_token = request.args.get('token')
    if not hook_token:
        return jsonify({'message': 'Token was not provided'}), 400

    found_mirror = PullMirror.query.filter_by(id=mirror_id).first()
    if not found_mirror:
        return jsonify({'message': 'Mirror not found'}), 404

    if found_mirror.hook_token != hook_token:
        return jsonify({'message': 'Supplied token was incorrect'}), 400

    if not found_mirror.project_id:
        return jsonify({'message': 'Project mirror is not created, cannot be synced'}), 400

    task = sync_pull_mirror.delay(found_mirror.id)
    log_task_pending(task, found_mirror, sync_pull_mirror, InvokedByEnum.HOOK)

    return jsonify({'message': 'Sync task started', 'uuid': task.id}), 200


@api_index.route('/push/sync/<int:mirror_id>', methods=['POST', 'GET'])
def schedule_sync_push_mirror(mirror_id: int) -> Tuple[flask.Response, int]:
    hook_token = request.args.get('token')
    if not hook_token:
        return jsonify({'message': 'Token was not provided'}), 400

    found_mirror = PushMirror.query.filter_by(id=mirror_id).first()
    if not found_mirror:
        return jsonify({'message': 'Mirror not found'}), 404

    if found_mirror.hook_token != hook_token:
        return jsonify({'message': 'Supplied token was incorrect'}), 400

    if not found_mirror.project_id:
        return jsonify({'message': 'Project mirror is not created, cannot be synced'}), 400

    task = sync_push_mirror.delay(found_mirror.id)
    log_task_pending(task, found_mirror, sync_push_mirror, InvokedByEnum.HOOK)

    return jsonify({'message': 'Sync task started', 'uuid': task.id}), 200


def group_fix_avatar(group: dict) -> dict:
    if not group['avatar_url']:
        group['avatar_url'] = url_for('static', filename='img/no_group_avatar.png', _external=True)
    return group


@api_index.route('/groups/search', methods=['GET'])
@login_required
def search_group() -> Tuple[flask.Response, int]:
    q = request.args.get('q')
    per_page = request.args.get('per_page')
    page = request.args.get('page')
    if not q:
        return jsonify({'message': 'q was not provided'}), 400

    gl = get_gitlab_instance()

    params = {
        'search': q,
        'as_list': False
    }

    if per_page:
        params['per_page'] = per_page

    if page:
        params['page'] = page

    items_list = gl.groups.list(**params)

    return jsonify({
        'items': [group_fix_avatar(i.attributes) for i in items_list],
        'current_page': items_list.current_page,
        'prev_page': items_list.prev_page,
        'next_page': items_list.next_page,
        'per_page': items_list.per_page,
        'total_pages': items_list.total_pages,
        'total': items_list.total,
    }), 200


@api_index.route('/groups/<int:group_id>', methods=['GET'])
@login_required
def get_gitlab_group(group_id: int) -> Tuple[flask.Response, int]:
    group = get_group(group_id)

    return jsonify(group_fix_avatar(group.attributes)), 200


@api_index.route('/projects/search', methods=['GET'])
@login_required
def search_project() -> Tuple[flask.Response, int]:
    q = request.args.get('q')
    per_page = request.args.get('per_page')
    page = request.args.get('page')
    if not q:
        return jsonify({'message': 'q was not provided'}), 400

    gl = get_gitlab_instance()

    params = {
        'search': q,
        'as_list': False
    }

    if per_page:
        params['per_page'] = per_page

    if page:
        params['page'] = page

    items_list = gl.projects.list(**params)

    return jsonify({
        'items': [i.attributes for i in items_list],
        'current_page': items_list.current_page,
        'prev_page': items_list.prev_page,
        'next_page': items_list.next_page,
        'per_page': items_list.per_page,
        'total_pages': items_list.total_pages,
        'total': items_list.total,
    }), 200


@api_index.route('/projects/<int:project_id>', methods=['GET'])
@login_required
def get_gitlab_project(project_id: int) -> Tuple[flask.Response, int]:
    project = get_project(project_id)

    return jsonify(project.attributes), 200


@api_index.route('/task/<string:task_id>/traceback', methods=['GET'])
@login_required
def get_task_traceback(task_id: str) -> Tuple[flask.Response, int]:
    task_meta = TaskMeta.query.filter_by(task_id=task_id).first_or_404()
    return jsonify({'traceback': task_meta.traceback}), 200
