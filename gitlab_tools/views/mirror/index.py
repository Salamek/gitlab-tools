
# -*- coding: utf-8 -*-

import flask
from flask_login import current_user, login_required
from gitlab_tools.models.gitlab_tools import db, Mirror, Group
from gitlab_tools.forms.mirror import EditForm, NewForm
from gitlab_tools.tools.helpers import random_password, detect_vcs_type
from gitlab_tools.blueprints import mirror_index
from gitlab_tools.tasks.gitlab_tools import sync_mirror, delete_mirror, add_mirror

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


def process_group(group: int) -> Group:
    found_group = Group.query.filter_by(gitlab_id=group).first()
    if not found_group:
        found_group = Group()
        found_group.gitlab_id = group
        db.session.add(found_group)
        db.session.commit()

    return found_group


@mirror_index.route('/', methods=['GET'], defaults={'page': 1})
@mirror_index.route('/page/<int:page>', methods=['GET'])
@login_required
def get_mirror(page: int):
    pagination = Mirror.query.filter_by(is_deleted=False, user=current_user).order_by(Mirror.created.desc()).paginate(page, PER_PAGE)
    return flask.render_template('mirror.index.mirror.html', pagination=pagination)


@mirror_index.route('/new', methods=['GET', 'POST'])
@login_required
def new_mirror():
    form = NewForm(
        flask.request.form,
        is_no_create=False,
        is_force_create=False,
        is_no_remote=False,
        is_issues_enabled=False,
        is_wall_enabled=False,
        is_wiki_enabled=False,
        is_snippets_enabled=False,
        is_merge_requests_enabled=False,
        is_public=False,
        is_force_update=False,
        is_prune_mirrors=False
    )
    if flask.request.method == 'POST' and form.validate():
        mirror_new = Mirror()
        mirror_new.project_name = form.project_name.data
        mirror_new.project_mirror = form.project_mirror.data
        mirror_new.vcs = detect_vcs_type(form.project_mirror.data)
        mirror_new.note = form.note.data
        mirror_new.is_no_create = form.is_no_create.data
        mirror_new.is_force_create = form.is_force_create.data
        mirror_new.is_no_remote = form.is_no_remote.data
        mirror_new.is_issues_enabled = form.is_issues_enabled.data
        mirror_new.is_wall_enabled = form.is_wall_enabled.data
        mirror_new.is_wiki_enabled = form.is_wiki_enabled.data
        mirror_new.is_snippets_enabled = form.is_snippets_enabled.data
        mirror_new.is_merge_requests_enabled = form.is_merge_requests_enabled.data
        mirror_new.is_public = form.is_public.data
        mirror_new.is_force_update = form.is_force_update.data
        mirror_new.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_new.hook_token = random_password()
        mirror_new.group = process_group(form.group.data)
        mirror_new.is_deleted = False
        mirror_new.user = current_user
        db.session.add(mirror_new)
        db.session.commit()

        add_mirror.delay(mirror_new.id)

        flask.flash('New mirror item was added successfully.', 'success')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))

    return flask.render_template('mirror.index.new.html', form=form)


@mirror_index.route('/edit/<int:mirror_id>', methods=['GET', 'POST'])
@login_required
def edit_mirror(mirror_id: int):
    # We dont have any edit functionality for mirrors, so just create new one and delete old one
    mirror_detail = Mirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    form = EditForm(
        flask.request.form,
        id=mirror_detail.id,
        vcs=mirror_detail.vcs,
        project_name=mirror_detail.project_name,
        project_mirror=mirror_detail.project_mirror,
        note=mirror_detail.note,
        is_no_create=mirror_detail.is_no_create,
        is_force_create=mirror_detail.is_force_create,
        is_no_remote=mirror_detail.is_no_remote,
        is_issues_enabled=mirror_detail.is_issues_enabled,
        is_wall_enabled=mirror_detail.is_wall_enabled,
        is_wiki_enabled=mirror_detail.is_wiki_enabled,
        is_snippets_enabled=mirror_detail.is_snippets_enabled,
        is_merge_requests_enabled=mirror_detail.is_merge_requests_enabled,
        is_public=mirror_detail.is_public,
        is_force_update=mirror_detail.is_force_update,
        is_prune_mirrors=mirror_detail.is_prune_mirrors,
        group=mirror_detail.group.gitlab_id
    )
    if flask.request.method == 'POST' and form.validate():
        # Add new mirror with new config
        mirror_detail.project_name = form.project_name.data
        mirror_detail.project_mirror = form.project_mirror.data
        mirror_detail.vcs = detect_vcs_type(form.project_mirror.data)
        mirror_detail.note = form.note.data
        mirror_detail.is_no_create = form.is_no_create.data
        mirror_detail.is_force_create = form.is_force_create.data
        mirror_detail.is_no_remote = form.is_no_remote.data
        mirror_detail.is_issues_enabled = form.is_issues_enabled.data
        mirror_detail.is_wall_enabled = form.is_wall_enabled.data
        mirror_detail.is_wiki_enabled = form.is_wiki_enabled.data
        mirror_detail.is_snippets_enabled = form.is_snippets_enabled.data
        mirror_detail.is_merge_requests_enabled = form.is_merge_requests_enabled.data
        mirror_detail.is_public = form.is_public.data
        mirror_detail.is_force_update = form.is_force_update.data
        mirror_detail.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_detail.group = process_group(form.group.data)
        mirror_detail.is_deleted = False
        mirror_detail.user = current_user

        db.session.add(mirror_detail)
        db.session.commit()

        # Create new mirror repo
        add_mirror.delay(mirror_detail.id)

        flask.flash('Mirror was saved successfully.', 'success')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))

    return flask.render_template('mirror.index.edit.html', form=form, mirror_detail=mirror_detail)


@mirror_index.route('/sync/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_sync_mirror(mirror_id: int):
    # Check if mirror exists or throw 404
    found_mirror = Mirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    if not found_mirror.gitlab_id:
        flask.flash('Mirror is not created, cannot be synced', 'danger')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))
    task = sync_mirror.delay(mirror_id)

    flask.flash('Sync has been started with UUID: {}'.format(task.id), 'success')
    return flask.redirect(flask.url_for('mirror.index.get_mirror'))


@mirror_index.route('/delete/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_delete_mirror(mirror_id: int):
    mirror_detail = Mirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    mirror_detail.is_deleted = True
    db.session.add(mirror_detail)
    db.session.commit()

    delete_mirror.delay(mirror_detail.id)

    flask.flash('Mirror was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('mirror.index.get_mirror'))
