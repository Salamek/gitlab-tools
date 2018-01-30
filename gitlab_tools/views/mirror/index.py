
# -*- coding: utf-8 -*-

import flask
from flask_login import current_user, login_required

from gitlab_tools.models.gitlab_tools import db, Mirror
from gitlab_tools.forms.mirror import EditForm, NewForm
from gitlab_tools.tools.helpers import random_password
from gitlab_tools.blueprints import mirror_index
from gitlab_tools.tasks.gitlab_tools import sync_mirror

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


@mirror_index.route('/', methods=['GET'], defaults={'page': 1})
@mirror_index.route('/page/<int:page>', methods=['GET'])
@login_required
def get_mirror(page: int):
    pagination = Mirror.query.filter().order_by(Mirror.created.desc()).paginate(page, PER_PAGE)
    return flask.render_template('mirror.index.mirror.html', pagination=pagination)


@mirror_index.route('/new', methods=['GET', 'POST'])
@login_required
def new_mirror():
    form = NewForm(flask.request.form)
    if flask.request.method == 'POST' and form.validate():
        mirror_new = Mirror()
        mirror_new.project_name = form.project_name.data
        mirror_new.project_mirror = form.project_mirror.data
        mirror_new.vcs = form.vcs.data
        mirror_new.direction = form.direction.data
        mirror_new.note = form.note.data
        mirror_new.hook_token = random_password()
        #mirror_new.last_sync = None
        db.session.add(mirror_new)
        db.session.commit()

        flask.flash('New mirror item was added successfully.', 'success')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))

    return flask.render_template('mirror.index.new.html', form=form)


@mirror_index.route('/edit/<int:mirror_id>', methods=['GET', 'POST'])
@login_required
def edit_mirror(mirror_id: int):
    mirror_detail = Mirror.query.filter_by(id=mirror_id).first_or_404()

    form = EditForm(
        flask.request.form,
        id=mirror_detail.id,
        vcs=mirror_detail.vcs,
        project_name=mirror_detail.project_name,
        project_mirror=mirror_detail.project_mirror,
        direction=mirror_detail.direction,
        note=mirror_detail.note,
    )
    if flask.request.method == 'POST' and form.validate():
        mirror_detail.project_name = form.project_name.data
        mirror_detail.project_mirror = form.project_mirror.data
        mirror_detail.vcs = form.vcs.data
        mirror_detail.direction = form.direction.data
        mirror_detail.note = form.note.data

        db.session.add(mirror_detail)
        db.session.commit()

        flask.flash('Mirror was saved successfully.', 'success')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))

    return flask.render_template('mirror.index.edit.html', form=form, mirror_detail=mirror_detail)


@mirror_index.route('/sync/<int:mirror_id>', methods=['GET'])
@login_required
def sync_mirror(mirror_id: int):
    # Check if mirror exists or throw 404
    Mirror.query.filter_by(id=mirror_id).first_or_404()
    task = sync_mirror.delay(mirror_id)

    flask.flash('Sync has been started with UUID: {}'.format(task.id), 'success')


@mirror_index.route('/delete/<int:mirror_id>', methods=['GET'])
@login_required
def delete_mirror(mirror_id: int):
    mirror_detail = Mirror.query.filter_by(id=mirror_id).first_or_404()
    db.session.delete(mirror_detail)
    db.session.commit()
    flask.flash('Mirror was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('mirror.index.get_mirror'))
