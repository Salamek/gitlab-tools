import subprocess
import os
import flask
import gitlab
import datetime
from Crypto.PublicKey import RSA
import requests
import shutil
from flask_celery import single_instance
from git import Repo
from gitlab_tools.models.gitlab_tools import Mirror, User
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.helpers import get_ssh_storage, get_repository_storage, get_user_public_key_path, get_user_private_key_path
from logging import getLogger
from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


def get_group_path(mirror: Mirror):
    repository_storage_path = get_repository_storage(flask.current_app.config['USER'])
    return os.path.join(repository_storage_path, str(mirror.group.id))


def get_repository_path(mirror: Mirror):
    # Check if project clone exists
    return os.path.join(get_group_path(mirror), str(mirror.id))


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

        # Check deploy key for this project
        if mirror.user.gitlab_deploy_key_id:
            # This mirror user have a deploy key ID, so just enable it if disabled
            if not project.keys.get(mirror.user.gitlab_deploy_key_id):
                project.keys.enable(mirror.user.gitlab_deploy_key_id)
        else:
            # No deploy key ID found, that means we need to add that key
            key = project.keys.create({
                'title': 'Gitlab tools deploy key for user {}'.format(mirror.user.name),
                'key': open(get_user_public_key_path(mirror.user, flask.current_app.config['USER'])).read(),
                'can_push': True # We need write access
            })

            mirror.user.gitlab_deploy_key_id = key.id

        mirror_remote = project.ssh_url_to_repo

        mirror.gitlab_id = project.id

        db.session.add(mirror)
        db.session.commit()

    else:
        mirror_remote = None

    # 2. Create/pull local repository

    repository_storage_group_path = get_group_path(mirror)

    # Check if repository storage group directory exists:
    if not os.path.isdir(repository_storage_group_path):
        os.mkdir(repository_storage_group_path)

    # Check if project clone exists
    project_path = get_repository_path(mirror)
    if os.path.isdir(project_path):
        repo = Repo(project_path)
        repo.remotes.origin.set_url(mirror.project_mirror)
        if not mirror.is_no_remote:
            repo.remotes.gitlab.set_url(mirror_remote)
    else:
        # Project not found, we can clone
        LOG.info('Creating mirror for {}'.format(mirror.project_mirror))

        # 3. Pull
        # 4. Push

        if mirror.vcs == VcsEnum.SVN:
            subprocess.Popen(
                ['git', 'svn', 'clone', mirror.project_mirror, mirror.project_name],
                cwd=repository_storage_group_path
            ).communicate()
            repo = Repo(project_path)
        else:
            repo = Repo.clone_from(mirror.project_mirror, project_path, mirror='pull')

            if mirror.vcs in [VcsEnum.BAZAAR, VcsEnum.MERCURIAL]:
                subprocess.Popen(
                    ['git', 'gc', '--aggressive'],
                    cwd=project_path
                )

        if not mirror.is_no_remote:
            LOG.info('Adding GitLab remote to project.')

            gitlab_remote = repo.create_remote('gitlab', mirror_remote, mirror='push')

            LOG.info('Checking the mirror into GitLab.')
            if mirror.vcs == VcsEnum.SVN:
                repo.reset(hard=True)  # 'git', 'reset', '--hard'

                subprocess.Popen(
                    ['git', 'svn', 'fetch'],
                    cwd=project_path
                ).communicate()
                """
                subprocess.Popen(
                    ['git', 'config', '--bool', 'core.bare', 'true'],
                    cwd=project_path
                )
                """
            else:
                repo.remotes.origin.fetch()

            gitlab_remote.push()

            """
            if mirror.vcs == VcsEnum.SVN:
                subprocess.Popen(
                    ['git', 'config', '--bool', 'core.bare', 'false'],
                    cwd=project_path
                )
            """

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

    repo = Repo(project_path)
    # Special code for SVN repo mirror
    if mirror.vcs == VcsEnum.SVN:
        """
        commands.append((
            project_path,
            ['git', 'config', '--bool', 'core.bare', 'false'],
        ))
        """
        repo.reset(hard=True)  # 'git', 'reset', '--hard'

        subprocess.Popen(
            ['git', 'svn', 'fetch'],
            cwd=project_path
        ).communicate()

        subprocess.Popen(
            ['git', 'svn', 'rebase'],
            cwd=project_path
        ).communicate()

        if not mirror.is_no_remote:
            """
            commands.append((
                project_path,
                ['git', 'config', '--bool', 'core.bare', 'true'],
            ))
            """
            repo.remotes.gitlab.push()
            """
            commands.append((
                project_path,
                ['git', 'config', '--bool', 'core.bare', 'false'],
            ))
            """

    else:
        # Everything else
        repo.remotes.origin.fetch(force=mirror.is_force_update, prune=mirror.is_prune_mirrors)
        repo.remotes.gitlab.push(force=mirror.is_force_update, prune=mirror.is_prune_mirrors)

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
    user = User.query.filter_by(id=user_id, is_rsa_pair_set=False).first()
    if user:
        # check if priv and pub keys exists
        private_key_path = get_user_private_key_path(user, flask.current_app.config['USER'])
        public_key_path = get_user_public_key_path(user, flask.current_app.config['USER'])

        if not os.path.isfile(private_key_path) or not os.path.isfile(public_key_path):

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
