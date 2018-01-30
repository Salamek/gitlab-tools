import subprocess
import os
import flask
import hashlib
import datetime
import requests
from flask_celery import single_instance
from sqlalchemy import or_
from logging import getLogger
from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_mirror(task_id: str, mirror_id: int) -> None:
    pass
