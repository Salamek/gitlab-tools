
# -*- coding: utf-8 -*-

import flask
from flask_login import current_user, login_required

from gitlab_tools.models.gitlab_tools import db, Mirror
from gitlab_tools.forms.mirror import EditForm, NewForm
from gitlab_tools.blueprints import mirror_index

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
    )
    if flask.request.method == 'POST' and form.validate():


        db.session.add(mirror_detail)
        db.session.commit()

        flask.flash('Mirror was saved successfully.', 'success')
        return flask.redirect(flask.url_for('mirror.index.get_mirror'))

    return flask.render_template('mirror.index.edit.html', form=form, mirror_detaill=mirror_detail)


@mirror_index.route('/delete/<int:mirror_id>', methods=['GET'])
@login_required
def delete_mirror(mirror_id: int):
    mirror_detail = Mirror.query.filter_by(id=mirror_id).first_or_404()
    db.session.delete(mirror_detail)
    db.session.commit()
    flask.flash('Mirror was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('mirror.index.get_mirror'))
