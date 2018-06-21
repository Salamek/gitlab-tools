
from sqlalchemy.exc import IntegrityError
from typing import Callable
from celery.result import AsyncResult
from gitlab_tools.models.gitlab_tools import Mirror, PullMirror, PushMirror, TaskResult
from gitlab_tools.extensions import db
from gitlab_tools.models.celery import TaskMeta
from gitlab_tools.enums.InvokedByEnum import InvokedByEnum


def log_task_pending(
        task: AsyncResult,
        mirror: Mirror,
        task_callable: Callable=None,
        invoked_by: int=InvokedByEnum.UNKNOWN,
        parent: TaskResult=None
) -> TaskResult:

    try:
        task_meta = TaskMeta()
        task_meta.task_id = task.id
        db.session.add(task_meta)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Wow it already exists, celery was so fast ?!
        # Lets make sure that result info have a correct data
        task_meta = TaskMeta.query.filter_by(task_id=task.id).first()
        db.session.add(task_meta)
        db.session.commit()

    task_result = TaskResult()
    task_result.taskmeta = task_meta
    task_result.parent = parent
    task_result.task_name = task_callable.__name__ if task_callable else None
    task_result.invoked_by = invoked_by
    if isinstance(mirror, PullMirror):
        task_result.pull_mirror = mirror
    elif isinstance(mirror, PushMirror):
        task_result.push_mirror = mirror

    db.session.add(task_result)
    db.session.commit()

    return task_result
