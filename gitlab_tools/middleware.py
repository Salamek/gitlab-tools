# -*- coding: utf-8 -*-

"""Flask middleware definitions. This is also where template filters are defined.

To be imported by the application.current_app() factory.
"""
import datetime
from typing import Optional
from logging import getLogger
from celery import states
from cron_descriptor import ExpressionDescriptor
from markupsafe import Markup
from flask import current_app, render_template
from flask_babel import format_datetime, format_date
from gitlab_tools.extensions import login_manager
from gitlab_tools.tools.formaters import format_bytes, fix_url, format_boolean, format_vcs
from gitlab_tools.enums.InvokedByEnum import InvokedByEnum
from gitlab_tools.models.gitlab_tools import User, TaskResult

LOG = getLogger(__name__)


# Setup default error templates.
@current_app.errorhandler(400)
@current_app.errorhandler(403)
@current_app.errorhandler(404)
@current_app.errorhandler(500)
def error_handler(e):
    code = getattr(e, 'code', 500)  # If 500, e == the exception.
    return render_template('{}.html'.format(code)), code


@login_manager.user_loader
def load_user(user_id) -> User:
    return User.query.get(user_id)


@current_app.before_request
def before_request():
    pass


@current_app.template_filter('format_bytes')
def format_bytes_filter(num: int) -> str:
    return format_bytes(num)


@current_app.template_filter('format_datetime')
def format_datetime_filter(date_time: datetime.datetime) -> str:
    return format_datetime(date_time)


@current_app.template_filter('format_date')
def format_date_filter(date_time: datetime.datetime) -> str:
    return format_date(date_time)


@current_app.template_filter('fix_url')
def fix_url_filter(url: str) -> str:
    return fix_url(url)


@current_app.template_filter('format_vcs')
def format_vcs_filter(vcs_enum: int) -> str:
    return format_vcs(vcs_enum)


@current_app.template_filter('format_boolean')
def format_boolean_filter(bool_to_format: bool) -> Markup:
    return Markup(format_boolean(bool_to_format))


@current_app.template_filter('format_cron_syntax')
def format_cron_syntax_filter(cron_syntax: Optional[str]) -> Optional[str]:
    if cron_syntax:
        expression_descriptor = ExpressionDescriptor(cron_syntax)
        return str(expression_descriptor)

    return None


@current_app.template_filter('format_task_status_class')
def format_task_status_class_filter(task_result: Optional[TaskResult] = None) -> str:
    if not task_result or not task_result.taskmeta:
        return 'warning'
    return {
        states.SUCCESS: 'success',
        states.FAILURE: 'danger',
        states.REVOKED: 'danger',
        states.REJECTED: 'danger',
        states.RETRY: 'warning',
        states.PENDING: 'info',
        states.RECEIVED: 'info',
        states.STARTED: 'info',
    }.get(task_result.taskmeta.status, 'warning')


@current_app.template_filter('format_task_invoked_by')
def format_task_invoked_by_filter(invoked_by: int) -> str:
    return {
        InvokedByEnum.MANUAL: 'Manual',
        InvokedByEnum.HOOK: 'Web hook',
        InvokedByEnum.SCHEDULER: 'Scheduler',
        InvokedByEnum.UNKNOWN: 'Unknown',
    }.get(invoked_by, 'Unknown')


# Template filters.
@current_app.template_filter()
def whitelist(value: str) -> Markup:
    """Whitelist specific HTML tags and strings.
    Positional arguments:
    value -- the string to perform the operation on.
    Returns:
    Markup() instance, indicating the string is safe.
    """
    translations = {
        '&amp;quot;': '&quot;',
        '&amp;#39;': '&#39;',
        '&amp;lsquo;': '&lsquo;',
        '&amp;nbsp;': '&nbsp;',
        '&lt;br&gt;': '<br>',
    }
    escaped = str(Markup.escape(value))  # Escapes everything.
    for k, v in translations.items():
        escaped = escaped.replace(k, v)  # Un-escape specific elements using str.replace.
    return Markup(escaped)  # Return as 'safe'.
