import os
import flask
import gitlab
import datetime
import paramiko
from Crypto.PublicKey import RSA
import shutil
from flask_celery import single_instance
from gitlab_tools.models.gitlab_tools import PullMirror, User
from gitlab_tools.tools.GitRemote import GitRemote
from gitlab_tools.tools.git import create_mirror, sync_mirror
from gitlab_tools.tools.helpers import get_repository_path, \
    get_namespace_path, \
    get_user_public_key_path, \
    get_user_private_key_path, \
    convert_url_for_user, \
    add_ssh_config, \
    mkdir_p
from logging import getLogger
from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


@celery.task(bind=True)
@single_instance(include_args=True)
def save_pull_mirror(mirror_id: int) -> None:
    mirror = PullMirror.query.filter_by(id=mirror_id).first()

    if not mirror.is_no_create and not mirror.is_no_remote:

        gl = gitlab.Gitlab(
            flask.current_app.config['GITLAB_URL'],
            oauth_token=mirror.user.access_token,
            api_version=flask.current_app.config['GITLAB_API_VERSION']
        )

        gl.auth()

        # 0. Check if group/s exists
        found_group = gl.groups.get(mirror.group.gitlab_id)
        if not found_group:
            raise Exception('Selected group ({}) not found'.format(mirror.group.gitlab_id))

        # 1. check if mirror exists in group/s if not create
        # If we have gitlab_id check if exists and use it if does, or create new project if not
        if mirror.gitlab_id:
            try:
                project = gl.projects.get(mirror.gitlab_id)
            except gitlab.exceptions.GitlabError as e:
                if e.response_code == 404:
                    project = None
                else:
                    raise

            # @TODO Project exists, lets check if it is in correct group ? This may not be needed if project.namespace_id bellow works
        else:
            project = None

        if project:
            # Update project
            project.name = mirror.project_name
            project.description = 'Mirror of {}.'.format(
                mirror.project_mirror
            )
            project.issues_enabled = mirror.is_issues_enabled
            project.wall_enabled = mirror.is_wall_enabled
            project.merge_requests_enabled = mirror.is_merge_requests_enabled
            project.wiki_enabled = mirror.is_wiki_enabled
            project.snippets_enabled = mirror.is_snippets_enabled
            project.public = mirror.is_public
            project.namespace_id = mirror.group.gitlab_id  # !FIXME is this enough to move it to different group ?
            project.save()
        else:
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
                'namespace_id': mirror.group.gitlab_id
            })

        # Check deploy key exists in gitlab
        key = None
        if mirror.user.gitlab_deploy_key_id:
            try:
                key = gl.deploykeys.get(mirror.user.gitlab_deploy_key_id)
            except gitlab.exceptions.GitlabError as e:
                if e.response_code == 404:
                    key = None
                else:
                    raise

            if key:
                # We got here, so key exists! lets check if its enabled for project
                try:
                    project.keys.get(mirror.user.gitlab_deploy_key_id)
                except gitlab.exceptions.GitlabError as e:
                    if e.response_code == 404:
                        # Enable if not enabled
                        project.keys.enable(mirror.user.gitlab_deploy_key_id)
                    else:
                        raise

        if not key:
            # No deploy key ID found, that means we need to add that key
            key = project.keys.create({
                'title': 'Gitlab tools deploy key for user {}'.format(mirror.user.name),
                'key': open(get_user_public_key_path(mirror.user, flask.current_app.config['USER'])).read(),
                'can_push': True  # We need write access
            })

            mirror.user.gitlab_deploy_key_id = key.id

        git_remote_target_original = GitRemote(
            project.ssh_url_to_repo,
            mirror.is_force_update,
            mirror.is_prune_mirrors
        )

        git_remote_target = GitRemote(
            convert_url_for_user(project.ssh_url_to_repo, mirror.user),
            mirror.is_force_update,
            mirror.is_prune_mirrors
        )

        add_ssh_config(
            mirror.user,
            flask.current_app.config['USER'],
            git_remote_target.hostname,
            git_remote_target_original.hostname
        )

        mirror.gitlab_id = project.id

        db.session.add(mirror)
        db.session.commit()

    else:
        git_remote_target = None

    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])

    # Check if repository storage group directory exists:
    if not os.path.isdir(namespace_path):
        mkdir_p(namespace_path)

    git_remote_source = GitRemote(mirror.source, mirror.is_force_update, mirror.is_prune_mirrors)

    create_mirror(namespace_path, str(mirror.id), git_remote_source, git_remote_target)

    # 5. Set last_sync date to mirror
    mirror.target = git_remote_target.url
    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_pull_mirror(mirror_id: int) -> None:
    mirror = PullMirror.query.filter_by(id=mirror_id).first()
    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])
    sync_mirror(namespace_path, mirror.id, GitRemote(mirror.source), GitRemote(mirror.target))

    # 5. Set last_sync date to mirror
    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def delete_mirror(mirror_id: int) -> None:
    mirror = PullMirror.query.filter_by(id=mirror_id, is_deleted=True).first()
    if mirror:
        # Check if project clone exists
        project_path = get_repository_path(
            get_namespace_path(
                mirror,
                flask.current_app.config['USER']
            ),
            mirror
        )
        if os.path.isdir(project_path):
            shutil.rmtree(project_path)

        db.session.delete(mirror)
        db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def create_rsa_pair(user_id: int) -> None:
    user = User.query.filter_by(id=user_id, is_rsa_pair_set=False).first()
    if user:
        # check if priv and pub keys exists
        private_key_path = get_user_private_key_path(user, flask.current_app.config['USER'])
        public_key_path = get_user_public_key_path(user, flask.current_app.config['USER'])

        key = RSA.generate(4096)
        with open(private_key_path, 'wb') as content_file:
            os.chmod(private_key_path, 0o0600)
            content_file.write(key.exportKey('PEM'))
        pubkey = key.publickey()
        with open(public_key_path, 'wb') as content_file:
            content_file.write(pubkey.exportKey('OpenSSH'))

        user.is_rsa_pair_set = True
        db.session.add(user)
        db.session.commit()


@celery.task(bind=True)
@single_instance()
def create_ssh_config(user_id: int, host: str, hostname: str) -> None:
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise Exception('User {} not found'.format(user_id))

    add_ssh_config(user, flask.current_app.config['USER'], host, hostname)
