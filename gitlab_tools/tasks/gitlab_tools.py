import subprocess
import os
import flask
import hashlib
import datetime
import requests
from flask_celery import single_instance
from sqlalchemy import or_
from gitlab_tools.models.gitlab_tools import Mirror
from logging import getLogger
from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_mirror(task_id: str, mirror_id: int) -> None:
    mirror = Mirror.query.filter(id=mirror_id).first()

    # 1. check if mirror exists in group/s if not create
    # 2. Create/pull local repository
    # 3. Add gitlab remote
    # 4. Push to gitlab remote
    # 5. Set last_sync date to mirror