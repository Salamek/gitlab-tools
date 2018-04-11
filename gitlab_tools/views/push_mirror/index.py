
# -*- coding: utf-8 -*-

import flask
from flask_login import current_user, login_required
from gitlab_tools.models.gitlab_tools import db, PushMirror, Project
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from gitlab_tools.forms.push_mirror import EditForm, NewForm
from gitlab_tools.tools.helpers import convert_url_for_user
from gitlab_tools.tools.crypto import random_password
from gitlab_tools.tools.GitRemote import GitRemote
from gitlab_tools.blueprints import push_mirror_index
from gitlab_tools.tasks.gitlab_tools import sync_push_mirror, \
    delete_push_mirror, \
    save_push_mirror, \
    create_ssh_config

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


def process_project(gitlab_id: int) -> Project:
    found_project = Project.query.filter_by(gitlab_id=gitlab_id).first()
    if not found_project:
        found_project = Project()
        found_project.gitlab_id = gitlab_id
        db.session.add(found_project)
        db.session.commit()

    return found_project


@push_mirror_index.route('/', methods=['GET'], defaults={'page': 1})
@push_mirror_index.route('/page/<int:page>', methods=['GET'])
@login_required
def get_mirror(page: int):
    pagination = PushMirror.query.filter_by(is_deleted=False, user=current_user).order_by(PushMirror.created.desc()).paginate(page, PER_PAGE)
    return flask.render_template('push_mirror.index.push_mirror.html', pagination=pagination)


@push_mirror_index.route('/new', methods=['GET', 'POST'])
@login_required
def new_mirror():
    form = NewForm(
        flask.request.form,
        is_force_update=False,
        is_prune_mirrors=False
    )
    if flask.request.method == 'POST' and form.validate():
        project_mirror = GitRemote(form.project_mirror.data)
        target = GitRemote(form.project_mirror.data)
        if target.vcs_protocol == ProtocolEnum.SSH:
            # If protocol is SSH we need to convert URL to use USER RSA pair
            target = GitRemote(convert_url_for_user(form.project_mirror.data, current_user))

        mirror_new = PushMirror()
        # PushMirror
        mirror_new.project_mirror = form.project_mirror.data
        mirror_new.project = process_project(form.project.data)

        # Mirror
        mirror_new.is_force_update = form.is_force_update.data
        mirror_new.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_new.is_deleted = False
        mirror_new.user = current_user
        mirror_new.foreign_vcs_type = target.vcs_type
        mirror_new.note = form.note.data
        mirror_new.target = target.url
        mirror_new.source = None  # We are getting source wia gitlab API
        mirror_new.last_sync = None
        mirror_new.hook_token = random_password()

        db.session.add(mirror_new)
        db.session.commit()

        if target.vcs_protocol == ProtocolEnum.SSH:
            # If target is SSH, create SSH Config for it also
            create_ssh_config.apply_async(
                (
                    current_user.id,
                    target.hostname,
                    project_mirror.hostname
                ),
                link=save_push_mirror.si(mirror_new.id)
            )
        else:
            save_push_mirror.delay(mirror_new.id)

        flask.flash('New push mirror item was added successfully.', 'success')
        return flask.redirect(flask.url_for('push_mirror.index.get_mirror'))

    return flask.render_template('push_mirror.index.new.html', form=form)


@push_mirror_index.route('/edit/<int:mirror_id>', methods=['GET', 'POST'])
@login_required
def edit_mirror(mirror_id: int):
    mirror_detail = PushMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    form = EditForm(
        flask.request.form,
        id=mirror_detail.id,
        project_mirror=mirror_detail.project_mirror,
        note=mirror_detail.note,
        is_force_update=mirror_detail.is_force_update,
        is_prune_mirrors=mirror_detail.is_prune_mirrors,
        project=mirror_detail.project.gitlab_id
    )
    if flask.request.method == 'POST' and form.validate():
        project_mirror = GitRemote(form.project_mirror.data)
        target = GitRemote(form.project_mirror.data)
        if target.vcs_protocol == ProtocolEnum.SSH:
            # If protocol is SSH we need to convert URL to use USER RSA pair
            target = GitRemote(convert_url_for_user(form.project_mirror.data, current_user))

        # PullMirror
        mirror_detail.project_mirror = form.project_mirror.data
        mirror_detail.project = process_project(form.project.data)

        # Mirror
        mirror_detail.is_force_update = form.is_force_update.data
        mirror_detail.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_detail.is_deleted = False
        mirror_detail.user = current_user
        mirror_detail.foreign_vcs_type = target.vcs_type
        mirror_detail.note = form.note.data
        mirror_detail.target = target
        mirror_detail.source = None  # We are getting source wia gitlab API

        db.session.add(mirror_detail)
        db.session.commit()

        if target.vcs_protocol == ProtocolEnum.SSH:
            # If source is SSH, create SSH COnfig for it also
            create_ssh_config.apply_async(
                (
                    current_user.id,
                    target.hostname,
                    project_mirror.hostname
                ),
                link=save_push_mirror.si(mirror_detail.id)
            )
        else:
            save_push_mirror.delay(mirror_detail.id)

        flask.flash('Push mirror was saved successfully.', 'success')
        return flask.redirect(flask.url_for('push_mirror.index.get_mirror'))

    return flask.render_template('push_mirror.index.edit.html', form=form, mirror_detail=mirror_detail)


@push_mirror_index.route('/sync/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_sync_mirror(mirror_id: int):
    # Check if mirror exists or throw 404
    found_mirror = PushMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    if not found_mirror.project_id:
        flask.flash('Project mirror is not created, cannot be synced', 'danger')
        return flask.redirect(flask.url_for('push_mirror.index.get_mirror'))
    task = sync_push_mirror.delay(mirror_id)

    flask.flash('Sync has been started with UUID: {}'.format(task.id), 'success')
    return flask.redirect(flask.url_for('push_mirror.index.get_mirror'))


@push_mirror_index.route('/delete/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_delete_mirror(mirror_id: int):
    mirror_detail = PushMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    mirror_detail.is_deleted = True
    db.session.add(mirror_detail)
    db.session.commit()

    delete_push_mirror.delay(mirror_detail.id)

    flask.flash('Push mirror was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('push_mirror.index.get_mirror'))
