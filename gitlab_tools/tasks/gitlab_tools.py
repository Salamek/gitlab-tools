import subprocess
import os
import flask
import gitlab
import datetime
from Crypto.PublicKey import RSA
import requests
import shutil
from flask_celery import single_instance
from sqlalchemy import or_
from gitlab_tools.models.gitlab_tools import Mirror, User
from gitlab_tools.enums.VcsEnum import VcsEnum
from logging import getLogger
from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


def get_group_path(mirror: Mirror):
    repository_storage_path = flask.current_app.config['REPOSITORY_STORAGE']
    return os.path.join(repository_storage_path, str(mirror.group.id))


def get_repository_path(mirror: Mirror):
    # Check if project clone exists
    return os.path.join(get_group_path(mirror), str(mirror.id))


def git_add_remote(commands, project_path, mirror_remote):
    LOG.info('Adding GitLab remote to project.')
    commands.append((
        project_path,
        ['git', 'remote', 'add', 'gitlab', mirror_remote],
    ))
    commands.append((
        project_path,
        ['git', 'config', '--add', 'remote.gitlab.push', '+refs/heads/*:refs/heads/*'],
    ))
    commands.append((
        project_path,
        ['git', 'config', '--add', 'remote.gitlab.push', '+refs/tags/*:refs/tags/*'],
    ))

    # !FIXME ???
    commands.append((
        project_path,
        ['git', 'config', 'remote.gitlab.mirror', 'true'],
    ))

    LOG.info('Checking the mirror into GitLab.')
    commands.append((
        project_path,
        ['git', 'fetch'],
    ))

    # !FIXME HTTP REMOTE
    if False:
        commands.append((
            project_path,
            ['git', 'config', 'credential.helper', 'store'],
        ))

    commands.append((
        project_path,
        ['git', 'push', 'gitlab'],
    ))


@celery.task(bind=True)
@single_instance(include_args=True)
def add_mirror(mirror_id: int) -> None:
    mirror = Mirror.query.filter_by(id=mirror_id).first()

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
    if not os.path.isdir(flask.current_app.config['REPOSITORY_STORAGE']):
        os.mkdir(flask.current_app.config['REPOSITORY_STORAGE'])

    repository_storage_group_path = get_group_path(mirror)

    # Check if repository storage group directory exists:
    if not os.path.isdir(repository_storage_group_path):
        os.mkdir(repository_storage_group_path)

    # Check if project clone exists
    project_path = get_repository_path(mirror)
    if not os.path.isdir(project_path):
        # Project not found, we can clone
        LOG.info('Creating mirror for {}'.format(mirror.project_mirror))

        # 3. Pull
        # 4. Push

        commands = []
        if mirror.vcs == VcsEnum.GIT:

            commands.append((
                repository_storage_group_path,
                ['git', 'clone', '--mirror', mirror.project_mirror, project_path]
            ))

            if not mirror.is_no_remote:
                git_add_remote(commands, project_path, mirror_remote)

        elif mirror.vcs == VcsEnum.SVN:
            commands.append((
                repository_storage_group_path,
                ['git', 'svn', 'clone',  mirror.project_mirror, mirror.project_name],
            ))

            if not mirror.is_no_remote:
                LOG.info('Adding GitLab remote to project.')
                commands.append((
                    project_path,
                    ['git', 'remote', 'add', 'gitlab', mirror_remote],
                ))
                commands.append((
                    project_path,
                    ['git', 'config', '--add', 'remote.gitlab.push', '+refs/heads/*:refs/heads/*'],
                ))
                commands.append((
                    project_path,
                    ['git', 'config', '--add', 'remote.gitlab.push', '+refs/remotes/*:refs/tags/*'],
                ))

                # !FIXME ???
                commands.append((
                    project_path,
                    ['git', 'config', 'remote.gitlab.mirror', 'true'],
                ))

                commands.append((
                    project_path,
                    ['git', 'reset', '--hard'],
                ))

                commands.append((
                    project_path,
                    ['git', 'svn', 'fetch'],
                ))

                commands.append((
                    project_path,
                    ['git', 'config', '--bool', 'core.bare', 'true'],
                ))

                if False:  # !FIXME HTTP REMOTE
                    commands.append((
                        project_path,
                        ['git', 'config', 'credential.helper', 'store'],
                    ))

                commands.append((
                    project_path,
                    ['git', 'push', 'gitlab'],
                ))

                commands.append((
                    project_path,
                    ['git', 'config', '--bool', 'core.bare', 'false'],
                ))

        elif mirror.vcs == VcsEnum.BAZAAR:
            commands.append((
                repository_storage_group_path,
                ['git', 'clone', '--mirror', 'bzr::{}'.format(mirror.project_mirror), mirror.project_name],
            ))

            commands.append((
                project_path,
                ['git', 'gc', '--aggressive'],
            ))

            if not mirror.is_no_remote:
                git_add_remote(commands, project_path, mirror_remote)

        elif mirror.vcs == VcsEnum.MERCURIAL:
            commands.append((
                repository_storage_group_path,
                ['git', 'clone', '--mirror', 'hg::{}'.format(mirror.project_mirror), mirror.project_name],
            ))
            commands.append((
                project_path,
                ['git', 'gc', '--aggressive'],
            ))

            if not mirror.is_no_remote:
                git_add_remote(commands, project_path, mirror_remote)

        for cwd, command in commands:
            subprocess.Popen(
                command,
                cwd=cwd
            ).communicate()

        LOG.info('All done!')

        # 5. Set last_sync date to mirror
        mirror.last_sync = datetime.datetime.now()
        db.session.add(mirror)
        db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_mirror(mirror_id: int) -> None:
    mirror = Mirror.query.filter_by(id=mirror_id).first()

    repository_storage_group_path = get_group_path(mirror)

    # Check if repository storage group directory exists:
    if not os.path.isdir(repository_storage_group_path):
        raise Exception('Group storage {} not found, creation failed ?'.format(repository_storage_group_path))

    # Check if project clone exists
    project_path = get_repository_path(mirror)
    if not os.path.isdir(project_path):
        raise Exception('Repository storage {} not found, creation failed ?'.format(project_path))

    commands = []
    # Special code for SVN repo mirror
    if mirror.vcs == VcsEnum.SVN:
        commands.append((
            project_path,
            ['git', 'config', '--bool', 'core.bare', 'false'],
        ))

        commands.append((
            project_path,
            ['git', 'reset', '--hard'],
        ))

        commands.append((
            project_path,
            ['git', 'svn', 'fetch'],
        ))

        commands.append((
            project_path,
            ['git', 'svn', 'rebase'],
        ))

        if not mirror.is_no_remote:
            commands.append((
                project_path,
                ['git', 'config', '--bool', 'core.bare', 'true'],
            ))

            commands.append((
                project_path,
                ['git', 'push', 'gitlab'],
            ))

            commands.append((
                project_path,
                ['git', 'config', '--bool', 'core.bare', 'false'],
            ))

    else:
        # Everything else
        cmd = ['git', 'fetch']
        if mirror.is_force_update:
            cmd.append('--force')
        if mirror.is_prune_mirrors:
            cmd.append('--prune')

        cmd.append('origin')
        commands.append((
            project_path,
            cmd
        ))

        cmd = ['git', 'push']
        if mirror.is_force_update:
            cmd.append('--force')
        if mirror.is_prune_mirrors:
            cmd.append('--prune')

        cmd.append('gitlab')
        commands.append((
            project_path,
            cmd
        ))

    for cwd, command in commands:
        subprocess.Popen(
            command,
            cwd=cwd
        ).communicate()

    LOG.info('Mirror sync done')


@celery.task(bind=True)
@single_instance(include_args=True)
def delete_mirror(mirror_id: int) -> None:
    mirror = Mirror.query.filter_by(id=mirror_id, is_deleted=True).first()
    if mirror:
        # Check if project clone exists
        project_path = get_repository_path(mirror)
        if os.path.isdir(project_path):
            shutil.rmtree(project_path)

        db.session.delete(mirror)
        db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def create_rsa_pair(user_id: int) -> None:
    ssh_storage = flask.current_app.config['SSH_STORAGE']
    user = User.query.find_by(id=user_id, is_rsa_pair_set=False).first()
    if user:
        # check if priv and pub keys exists
        private_key_path = os.path.join(ssh_storage, 'id_rsa_{}'.format(user.id))
        public_key_path = os.path.join(ssh_storage, 'id_rsa_{}.pub'.format(user.id))

        if not os.path.isfile(private_key_path) or not os.path.isfile(public_key_path):

            key = RSA.generate(2048)
            with open(private_key_path, 'w') as content_file:
                os.chmod(private_key_path, 0o0600)
                content_file.write(key.exportKey('PEM'))
            pubkey = key.publickey()
            with open(public_key_path, 'w') as content_file:
                content_file.write(pubkey.exportKey('OpenSSH'))

            user.is_rsa_pair_set = True
            db.session.add(user)
            db.session.commit()
