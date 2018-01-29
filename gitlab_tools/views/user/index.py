
# -*- coding: utf-8 -*-

import flask
from flask_login import current_user, login_required

from gitlab_tools.models.gitlab_tools import User, db, Role
from gitlab_tools.tools.Acl import Acl
from gitlab_tools.forms.user import EditForm, NewForm
from gitlab_tools.blueprints import user_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"

PER_PAGE = 20


@user_index.route('/', methods=['GET'], defaults={'page': 1})
@user_index.route('/page/<int:page>', methods=['GET'])
@login_required
@Acl.validate_path([Role.ADMIN], current_user)
def get_user(page: int):
    pagination = User.query.filter().order_by(User.created.desc()).paginate(page, PER_PAGE)
    return flask.render_template('user.index.user.html', pagination=pagination)


@user_index.route('/new', methods=['GET', 'POST'])
@login_required
@Acl.validate_path([Role.ADMIN], current_user)
def new_user():
    form = NewForm(flask.request.form)
    if flask.request.method == 'POST' and form.validate():
        user_new = User()
        user_new.username = form.username.data
        user_new.roles = Role.query.filter(Role.id.in_(form.roles.data)).all()
        user_new.set_password(form.password.data)
        db.session.add(user_new)
        db.session.commit()
        flask.flash('New user was added successfully.', 'success')
        return flask.redirect(flask.url_for('user.index.get_user'))

    return flask.render_template('user.index.new.html', form=form)


@user_index.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@Acl.validate_path([Role.ADMIN], current_user)
@login_required
def edit_user(user_id: int):
    user_detail = User.query.filter_by(id=user_id).first_or_404()

    roles = []
    for role in user_detail.roles:
        roles.append(role.id)

    form = EditForm(flask.request.form, username=user_detail.username, id=user_detail.id, roles=roles)
    if flask.request.method == 'POST' and form.validate():
        if form.password.data:
            user_detail.set_password(form.password.data)
            flask.flash('User password has been changed.', 'success')

        user_detail.roles = Role.query.filter(Role.id.in_(form.roles.data)).all()
        user_detail.username = form.username.data
        db.session.add(user_detail)
        db.session.commit()
        flask.flash('User was saved successfully.', 'success')
        return flask.redirect(flask.url_for('user.index.get_user'))

    return flask.render_template('user.index.edit.html', form=form, user_detail=user_detail)


@user_index.route('/delete/<int:user_id>', methods=['GET'])
@login_required
@Acl.validate_path([Role.ADMIN], current_user)
def delete_user(user_id: int):
    user_detail = User.query.filter_by(id=user_id).first_or_404()
    db.session.delete(user_detail)
    db.session.commit()
    flask.flash('User was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('user.index.get_user'))
