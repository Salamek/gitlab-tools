
# -*- coding: utf-8 -*-

import flask
import json
from flask_login import current_user, login_required
from gitlab_tools.models.gitlab_tools import PullMirror, Group
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from gitlab_tools.forms.pull_mirror import EditForm, NewForm
from gitlab_tools.tools.helpers import convert_url_for_user
from gitlab_tools.tools.crypto import random_password
from gitlab_tools.tools.GitRemote import GitRemote
from gitlab_tools.models.celery_beat import PeriodicTask, CrontabSchedule, PeriodicTasks
from cron_descriptor.ExpressionParser import ExpressionParser
from cron_descriptor.Options import Options
from gitlab_tools.blueprints import pull_mirror_index
from gitlab_tools.extensions import db
from gitlab_tools.tasks.gitlab_tools import sync_pull_mirror, \
    delete_pull_mirror, \
    save_pull_mirror, \
    create_ssh_config


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


def process_cron_expression(pull_mirror: PullMirror) -> bool:
    """

    :param pull_mirror: 
    :return: 
    """
    changed = False
    if pull_mirror.periodic_sync:
        expression_parser = ExpressionParser(pull_mirror.periodic_sync, Options())
        second, minute, hour, day_of_week, day_of_month, month_of_year, foo_ = expression_parser.parse()

        parameters = dict(
            minute=minute,
            hour=hour,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            month_of_year=month_of_year
        )

        crontab_schedule = CrontabSchedule.query.filter_by(**parameters).first()
        if not crontab_schedule:
            crontab_schedule = CrontabSchedule(
                minute=minute,
                hour=hour,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                month_of_year=month_of_year
            )
            db.session.add(crontab_schedule)

        if pull_mirror.periodic_task and pull_mirror.periodic_task.crontab == crontab_schedule:
            # We have same config. ignore
            return False

        # Delete od periodic task
        if pull_mirror.periodic_task:
            db.session.delete(pull_mirror.periodic_task)

        periodic_task = PeriodicTask(
            name="PullMirror (id:{}) periodic task {}".format(pull_mirror.id, pull_mirror.periodic_sync),
            task="gitlab_tools.tasks.gitlab_tools.sync_pull_mirror",
            crontab=crontab_schedule,
            args=json.dumps([pull_mirror.id]),
            kwargs=json.dumps({})
        )
        db.session.add(periodic_task)
        pull_mirror.periodic_task = periodic_task
        changed = True
    elif pull_mirror.periodic_task:
        # Find if any other PeriodicTask uses that CrontabSchedule
        if not PeriodicTask.query.filter(
                        PeriodicTask.crontab == pull_mirror.periodic_task.crontab,
                        PeriodicTask.id != pull_mirror.periodic_task.id
        ).first():
            db.session.delete(pull_mirror.periodic_task.crontab)

        db.session.delete(pull_mirror.periodic_task)

        pull_mirror.periodic_task = None
        changed = True
    db.session.add(pull_mirror)
    return changed


@pull_mirror_index.route('/', methods=['GET'], defaults={'page': 1})
@pull_mirror_index.route('/page/<int:page>', methods=['GET'])
@login_required
def get_mirror(page: int):
    pagination = PullMirror.query.filter_by(is_deleted=False, user=current_user).order_by(PullMirror.created.desc()).paginate(page, PER_PAGE)
    return flask.render_template('pull_mirror.index.pull_mirror.html', pagination=pagination)


@pull_mirror_index.route('/new', methods=['GET', 'POST'])
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
        is_prune_mirrors=False,
        is_builds_enabled=True
    )
    if flask.request.method == 'POST' and form.validate():
        project_mirror = GitRemote(form.project_mirror.data)
        source = GitRemote(form.project_mirror.data)
        if source.vcs_protocol == ProtocolEnum.SSH:
            # If protocol is SSH we need to convert URL to use USER RSA pair
            source = GitRemote(convert_url_for_user(form.project_mirror.data, current_user))

        mirror_new = PullMirror()
        # PullMirror
        mirror_new.project_name = form.project_name.data
        mirror_new.project_mirror = form.project_mirror.data
        mirror_new.is_no_create = form.is_no_create.data
        mirror_new.is_force_create = form.is_force_create.data
        mirror_new.is_no_remote = form.is_no_remote.data
        mirror_new.is_issues_enabled = form.is_issues_enabled.data
        mirror_new.is_wall_enabled = form.is_wall_enabled.data
        mirror_new.is_wiki_enabled = form.is_wiki_enabled.data
        mirror_new.is_snippets_enabled = form.is_snippets_enabled.data
        mirror_new.is_builds_enabled = form.is_builds_enabled.data
        mirror_new.is_merge_requests_enabled = form.is_merge_requests_enabled.data
        mirror_new.is_public = form.is_public.data
        mirror_new.group = process_group(form.group.data)
        mirror_new.periodic_sync = form.periodic_sync.data

        # Mirror
        mirror_new.is_force_update = form.is_force_update.data
        mirror_new.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_new.is_deleted = False
        mirror_new.user = current_user
        mirror_new.foreign_vcs_type = source.vcs_type
        mirror_new.note = form.note.data
        mirror_new.target = None  # We are getting target wia gitlab API
        mirror_new.source = source.url
        mirror_new.last_sync = None
        mirror_new.hook_token = random_password()

        if process_cron_expression(mirror_new):
            PeriodicTasks.changed()

        db.session.add(mirror_new)
        db.session.commit()

        if source.vcs_protocol == ProtocolEnum.SSH:
            # If source is SSH, create SSH Config for it also
            create_ssh_config.apply_async(
                (
                    current_user.id,
                    source.hostname,
                    project_mirror.hostname
                ),
                link=save_pull_mirror.si(mirror_new.id)
            )
        else:
            save_pull_mirror.delay(mirror_new.id)

        flask.flash('New pull mirror item was added successfully.', 'success')
        return flask.redirect(flask.url_for('pull_mirror.index.get_mirror'))

    return flask.render_template('pull_mirror.index.new.html', form=form)


@pull_mirror_index.route('/edit/<int:mirror_id>', methods=['GET', 'POST'])
@login_required
def edit_mirror(mirror_id: int):
    mirror_detail = PullMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    form = EditForm(
        flask.request.form,
        id=mirror_detail.id,
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
        group=mirror_detail.group.gitlab_id,
        periodic_sync=mirror_detail.periodic_sync,
        is_builds_enabled=mirror_detail.is_builds_enabled
    )
    if flask.request.method == 'POST' and form.validate():
        project_mirror = GitRemote(form.project_mirror.data)
        source = GitRemote(form.project_mirror.data)
        if source.vcs_protocol == ProtocolEnum.SSH:
            # If protocol is SSH we need to convert URL to use USER RSA pair
            source = GitRemote(convert_url_for_user(form.project_mirror.data, current_user))

        # PullMirror
        mirror_detail.project_name = form.project_name.data
        mirror_detail.project_mirror = form.project_mirror.data
        mirror_detail.is_no_create = form.is_no_create.data
        mirror_detail.is_force_create = form.is_force_create.data
        mirror_detail.is_no_remote = form.is_no_remote.data
        mirror_detail.is_issues_enabled = form.is_issues_enabled.data
        mirror_detail.is_wall_enabled = form.is_wall_enabled.data
        mirror_detail.is_wiki_enabled = form.is_wiki_enabled.data
        mirror_detail.is_snippets_enabled = form.is_snippets_enabled.data
        mirror_detail.is_builds_enabled = form.is_builds_enabled.data
        mirror_detail.is_merge_requests_enabled = form.is_merge_requests_enabled.data
        mirror_detail.is_public = form.is_public.data
        mirror_detail.group = process_group(form.group.data)
        mirror_detail.periodic_sync = form.periodic_sync.data

        # Mirror
        mirror_detail.is_force_update = form.is_force_update.data
        mirror_detail.is_prune_mirrors = form.is_prune_mirrors.data
        mirror_detail.is_deleted = False
        mirror_detail.user = current_user
        mirror_detail.foreign_vcs_type = source.vcs_type
        mirror_detail.note = form.note.data
        mirror_detail.target = None  # We are getting target wia gitlab API
        mirror_detail.source = source.url

        if process_cron_expression(mirror_detail):
            PeriodicTasks.changed()

        db.session.add(mirror_detail)
        db.session.flush()
        db.session.commit()
        if source.vcs_protocol == ProtocolEnum.SSH:
            # If source is SSH, create SSH Config for it also
            create_ssh_config.apply_async(
                (
                    current_user.id,
                    source.hostname,
                    project_mirror.hostname
                ),
                link=save_pull_mirror.si(mirror_detail.id)
            )
        else:
            save_pull_mirror.delay(mirror_detail.id)

        flask.flash('Pull mirror was saved successfully.', 'success')
        return flask.redirect(flask.url_for('pull_mirror.index.get_mirror'))

    return flask.render_template('pull_mirror.index.edit.html', form=form, mirror_detail=mirror_detail)


@pull_mirror_index.route('/sync/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_sync_mirror(mirror_id: int):
    # Check if mirror exists or throw 404
    found_mirror = PullMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    if not found_mirror.project_id:
        flask.flash('Project mirror is not created, cannot be synced', 'danger')
        return flask.redirect(flask.url_for('pull_mirror.index.get_mirror'))
    task = sync_pull_mirror.delay(mirror_id)

    flask.flash('Sync has been started with UUID: {}'.format(task.id), 'success')
    return flask.redirect(flask.url_for('pull_mirror.index.get_mirror'))


@pull_mirror_index.route('/delete/<int:mirror_id>', methods=['GET'])
@login_required
def schedule_delete_mirror(mirror_id: int):
    mirror_detail = PullMirror.query.filter_by(id=mirror_id, user=current_user).first_or_404()
    mirror_detail.is_deleted = True
    db.session.add(mirror_detail)
    db.session.commit()

    delete_pull_mirror.delay(mirror_detail.id)

    flask.flash('Pull mirror was deleted successfully.', 'success')

    return flask.redirect(flask.url_for('pull_mirror.index.get_mirror'))
