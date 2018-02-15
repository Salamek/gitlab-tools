import subprocess
import os
import flask
import gitlab
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
    repository_storage_path = flask.current_app.config['REPOSITORY_STORAGE']
    mirror = Mirror.query.filter(id=mirror_id).first()

    if not mirror.is_no_create and not mirror.is_no_remote:

        gl = gitlab.Gitlab(
            flask.current_app.config['GITLAB_URL'],
            oauth_token=mirror.user.access_token,
            api_version=flask.current_app.config['GITLAB_API_VERSION']
        )

        gl.auth()

        # 0. Check if group/s exists
        found_group = gl.groups.get(mirror.group.id)
        if not found_group:
            raise Exception('Selected group ({}) not found'.format(mirror.group.id))

        # 1. check if mirror exists in group/s if not create
        # If we have gitlab_id check if exists and use it if does, or create new project if not
        if mirror.gitlab_id:
            project = gl.projects.get(mirror.gitlab_id)

            # @TODO Project exists, lets check if it is in correct group ?
        else:
            project = None

        if not project:
            project = gl.projects.create({
                'name': mirror.project_name,
                'description': 'Mirror of {}.'.format(
                    mirror.project_mirror
                ),
                'issues_enabled': mirror.is_issues_enabled,
                'wall_enabled': mirror.is_wall_enabled,
                'merge_requests_enabled': mirror.is_merge_requests_enabled,
                'wiki_enabled': mirror.is_wiki_enabled,
                'snippets_enabled': mirror.is_snippets_enabled,
                'public': mirror.is_public,
                'namespace_id': mirror.group.id
            })

        mirror_remote = project.ssh_url_to_repo

        mirror.gitlab_id = project.id

        db.session.add(mirror)
        db.session.commit()

    else:
        mirror_remote = None

    # 2. Create/pull local repository

    # Check if repository storage directory exists
    if not os.path.isdir(repository_storage_path):
        os.mkdir(repository_storage_path)

    repository_storage_group_path = os.path.join(repository_storage_path, mirror.group.id)

    # Check if repository storage group directory exists:
    if not os.path.isdir(repository_storage_group_path):
        os.mkdir(repository_storage_group_path)

    # Check if project clone exists
    if not os.path.isdir(os.path.join(repository_storage_group_path, mirror.project_name)):
        # Project not found, we can clone
        subprocess.Popen(
            ['git', 'clone', '--mirror', mirror.project_mirror, mirror.project_name],
            cwd=repository_storage_group_path
        )



    # 3. Add gitlab remote
    # 4. Push to gitlab remote
    # 5. Set last_sync date to mirror
