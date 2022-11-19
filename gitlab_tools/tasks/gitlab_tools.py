import os
import datetime
import shutil
from logging import getLogger
import flask
import gitlab

from Cryptodome.PublicKey import RSA

from flask_celery import single_instance
from gitlab_tools.models.gitlab_tools import PullMirror, User, PushMirror, Project
from gitlab_tools.tools.GitRemote import GitRemote
from gitlab_tools.tools.GitUri import GitUri
from gitlab_tools.tools.celery import log_task_pending
from gitlab_tools.tools.Git import Git
from gitlab_tools.enums.InvokedByEnum import InvokedByEnum
from gitlab_tools.tools.helpers import get_repository_path, \
    get_namespace_path, \
    get_user_public_key_path, \
    get_user_private_key_path, \
    convert_url_for_user, \
    add_ssh_config, \
    mkdir_p

from gitlab_tools.extensions import celery, db


LOG = getLogger(__name__)


@celery.task(bind=True)
@single_instance(include_args=True)
def save_pull_mirror(self, mirror_id: int) -> None:  # pylint: disable=unused-argument, too-many-locals, too-many-statements, too-many-branches
    mirror = PullMirror.query.filter_by(id=mirror_id).first()
    gl = None  # !FIXME this is here cos hotfix on the end of script
    gitlab_project = None  # !FIXME this is here cos hotfix on the end of script
    if not mirror.is_no_create and not mirror.is_no_remote:

        gl = gitlab.Gitlab(
            flask.current_app.config['GITLAB_URL'],
            oauth_token=mirror.user.access_token,
            api_version=flask.current_app.config['GITLAB_API_VERSION']
        )

        gl.auth()

        # 0. Check if group/s exists
        try:
            gl.groups.get(mirror.group.gitlab_id)
        except gitlab.exceptions.GitlabError as e:
            if e.response_code == 404:
                raise Exception('Selected group ({}) not found'.format(mirror.group.gitlab_id)) from e
            raise e

        # 1. check if project mirror exists in group/s if not create
        # If we have project_id check if exists and use it if does, or create new project if not
        if mirror.project_id:
            try:
                gitlab_project = gl.projects.get(mirror.project.gitlab_id)
            except gitlab.exceptions.GitlabError as e:
                if e.response_code == 404:
                    gitlab_project = None
                else:
                    raise

            # @TODO Project exists, lets check if it is in correct group?
            #  This may not be needed if project.namespace_id bellow works
        else:
            gitlab_project = None

        if gitlab_project:
            # Update project
            gitlab_project.name = mirror.project_name
            gitlab_project.description = 'Mirror of {}.'.format(
                mirror.project_mirror
            )
            gitlab_project.issues_enabled = mirror.is_issues_enabled
            gitlab_project.jobs_enabled = mirror.is_jobs_enabled
            gitlab_project.wall_enabled = mirror.is_wall_enabled
            gitlab_project.merge_requests_enabled = mirror.is_merge_requests_enabled
            gitlab_project.wiki_enabled = mirror.is_wiki_enabled
            gitlab_project.snippets_enabled = mirror.is_snippets_enabled
            gitlab_project.visibility = mirror.visibility
            gitlab_project.namespace_id = mirror.group.gitlab_id  # !FIXME is this enough to move it to different group ?
            gitlab_project.save()
        else:
            try:
                gitlab_project = gl.projects.create({
                    'name': mirror.project_name,
                    'description': 'Mirror of {}.'.format(
                        mirror.project_mirror
                    ),
                    'issues_enabled': mirror.is_issues_enabled,
                    'wall_enabled': mirror.is_wall_enabled,
                    'merge_requests_enabled': mirror.is_merge_requests_enabled,
                    'wiki_enabled': mirror.is_wiki_enabled,
                    'snippets_enabled': mirror.is_snippets_enabled,
                    'visibility': mirror.visibility,
                    'namespace_id': mirror.group.gitlab_id,
                    'jobs_enabled': mirror.is_jobs_enabled
                })
            except gitlab.exceptions.GitlabCreateError as e:
                if e.response_code == 400:
                    # Name already taken
                    if not mirror.is_force_create:
                        raise e

                    # Force create enabled, lets find our project
                    found_projects = gl.projects.list(search=mirror.project_name)
                    for found_project in found_projects:
                        if mirror.project_name in [found_project.name, found_project.path] and \
                                mirror.group.gitlab_id == int(found_project.namespace['id']):
                            gitlab_project = gl.projects.get(found_project.id)
                            break

            # !FIXME BUG Trigger housekeeping right after creation to prevent ugly 404/500 project detail bug
            # !FIXME BUG See https://gitlab.com/gitlab-org/gitlab-ce/issues/43825
            gl.http_post('/projects/{project_id}/housekeeping'.format(project_id=gitlab_project.id))

            found_project = Project.query.filter_by(gitlab_id=gitlab_project.id).first()
            if not found_project:
                found_project = Project()
                found_project.gitlab_id = gitlab_project.id
            found_project.name = gitlab_project.name
            found_project.name_with_namespace = gitlab_project.name_with_namespace
            found_project.web_url = gitlab_project.web_url
            db.session.add(found_project)
            db.session.commit()

            mirror.project_id = found_project.id
            db.session.add(mirror)
            db.session.commit()

        # Check deploy key exists in gitlab
        key = None
        if mirror.user.gitlab_deploy_key_id:
            try:
                try:
                    key = gl.deploykeys.get(mirror.user.gitlab_deploy_key_id)
                except AttributeError:
                    # python-gitlab > 1.5 has no get on DeployKeysManager
                    for key_item in gl.deploykeys.list():
                        if key_item.id == mirror.user.gitlab_deploy_key_id:
                            key = key_item
                            break
            except gitlab.exceptions.GitlabError as e:
                if e.response_code == 404:
                    key = None
                else:
                    raise

            if key:
                # We got here, so key exists! lets check if its enabled for project
                try:
                    gitlab_project.keys.get(mirror.user.gitlab_deploy_key_id)
                except gitlab.exceptions.GitlabError as e:
                    if e.response_code == 404:
                        # Enable if not enabled
                        gitlab_project.keys.enable(mirror.user.gitlab_deploy_key_id)
                    else:
                        raise

                enabled_key = gitlab_project.keys.get(mirror.user.gitlab_deploy_key_id)
                gl.http_put(
                    '/projects/{project_id}/deploy_keys/{key_id}'.format(
                        project_id=gitlab_project.id,
                        key_id=enabled_key.id
                    ),
                    post_data={
                        'can_push': True
                    }
                )
                # Make sure that key has can_push=True
                # !FIXME Enable when implemented
                # enabled_key = project.keys.get(mirror.user.gitlab_deploy_key_id)
                # enabled_key.can_push = True
                # enabled_key.save()

        if not key:
            # No deploy key ID found, that means we need to add that key
            key = gitlab_project.keys.create({
                'title': 'Gitlab tools deploy key for user {}'.format(mirror.user.name),
                'key': open(get_user_public_key_path(mirror.user, flask.current_app.config['USER'])).read(),
                'can_push': True  # We need write access
            })

            mirror.user.gitlab_deploy_key_id = key.id
            db.session.add(mirror)
            db.session.commit()

        git_remote_target_original = GitRemote(
            gitlab_project.ssh_url_to_repo,
            mirror.is_force_update,
            mirror.is_prune_mirrors
        )

        git_remote_target = GitRemote(
            convert_url_for_user(gitlab_project.ssh_url_to_repo, mirror.user),
            mirror.is_force_update,
            mirror.is_prune_mirrors
        )

        add_ssh_config(
            mirror.user,
            flask.current_app.config['USER'],
            git_remote_target.hostname,
            git_remote_target_original
        )
        mirror.target = git_remote_target.url
        db.session.add(mirror)
        db.session.commit()
    else:
        git_remote_target = None

    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])

    # Check if repository storage group directory exists:
    if not os.path.isdir(namespace_path):
        mkdir_p(namespace_path)

    git_remote_source = GitRemote(mirror.source, mirror.is_force_update, mirror.is_prune_mirrors)

    Git.create_mirror(namespace_path, str(mirror.id), git_remote_source, git_remote_target)

    if gl and gitlab_project:
        # !FIXME BUG Trigger housekeeping right after mirror sync to reload homepage of project
        # !FIXME BUG Somehow i'm unable to reproduce this in simple script :/ to report this bug
        gl.http_post('/projects/{project_id}/housekeeping'.format(project_id=gitlab_project.id))

    # 5. Set last_sync date to mirror

    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def save_push_mirror(self, push_mirror_id) -> None:  # pylint: disable=unused-argument, too-many-statements
    mirror = PushMirror.query.filter_by(id=push_mirror_id).first()
    gl = gitlab.Gitlab(
        flask.current_app.config['GITLAB_URL'],
        oauth_token=mirror.user.access_token,
        api_version=flask.current_app.config['GITLAB_API_VERSION']
    )

    gl.auth()

    # 0. Check if project exists
    gitlab_project = gl.projects.get(mirror.project.gitlab_id)
    if not gitlab_project:
        raise Exception('Selected group ({}) not found'.format(mirror.project.gitlab_id))

    found_project = Project.query.filter_by(gitlab_id=gitlab_project.id).first()
    if not found_project:
        found_project = Project()
        found_project.gitlab_id = gitlab_project.id
    found_project.name = gitlab_project.name
    found_project.name_with_namespace = gitlab_project.name_with_namespace
    found_project.web_url = gitlab_project.web_url
    db.session.add(found_project)
    db.session.commit()

    # Check deploy key exists in gitlab
    key = None
    if mirror.user.gitlab_deploy_key_id:
        try:
            try:
                key = gl.deploykeys.get(mirror.user.gitlab_deploy_key_id)
            except AttributeError:
                # python-gitlab > 1.5 has no get on DeployKeysManager
                for key_item in gl.deploykeys.list():
                    if key_item.id == mirror.user.gitlab_deploy_key_id:
                        key = key_item
                        break
        except gitlab.exceptions.GitlabError as e:
            if e.response_code == 404:
                key = None
            else:
                raise

        if key:
            # We got here, so key exists! lets check if its enabled for project
            try:
                gitlab_project.keys.get(mirror.user.gitlab_deploy_key_id)
            except gitlab.exceptions.GitlabError as e:
                if e.response_code == 404:
                    # Enable if not enabled
                    gitlab_project.keys.enable(mirror.user.gitlab_deploy_key_id)
                else:
                    raise

    if not key:
        # No deploy key ID found, that means we need to add that key
        key = gitlab_project.keys.create({
            'title': 'Gitlab tools deploy key for user {}'.format(mirror.user.name),
            'key': open(get_user_public_key_path(mirror.user, flask.current_app.config['USER'])).read()
        })

        mirror.user.gitlab_deploy_key_id = key.id
        db.session.add(mirror)
        db.session.commit()

    # Create hook
    gitlab_project.hooks.create({
        'url': flask.url_for(
            'api_index.schedule_sync_push_mirror',
            mirror_id=mirror.id,
            token=mirror.hook_token,
            _external=True
        ),
        'push_events': True,
        'tag_push_events': True
    })

    git_remote_source_original = GitRemote(
        gitlab_project.ssh_url_to_repo,
        mirror.is_force_update,
        mirror.is_prune_mirrors
    )

    git_remote_source = GitRemote(
        convert_url_for_user(gitlab_project.ssh_url_to_repo, mirror.user),
        mirror.is_force_update,
        mirror.is_prune_mirrors
    )

    add_ssh_config(
        mirror.user,
        flask.current_app.config['USER'],
        git_remote_source.hostname,
        git_remote_source_original
    )

    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])

    # Check if repository storage group directory exists:
    if not os.path.isdir(namespace_path):
        mkdir_p(namespace_path)

    git_remote_target = GitRemote(mirror.target, mirror.is_force_update, mirror.is_prune_mirrors)

    Git.create_mirror(namespace_path, str(mirror.id), git_remote_source, git_remote_target)

    # 5. Set last_sync date to mirror
    mirror.source = git_remote_source_original.url
    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_pull_mirror_cron(self, pull_mirror_id: int) -> None:  # pylint: disable=unused-argument
    pull_mirror = PullMirror.query.filter_by(id=pull_mirror_id).first()

    task = sync_pull_mirror.delay(pull_mirror_id)
    log_task_pending(task, pull_mirror, sync_pull_mirror, InvokedByEnum.SCHEDULER)


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_pull_mirror(self, pull_mirror_id: int) -> None:  # pylint: disable=unused-argument
    mirror = PullMirror.query.filter_by(id=pull_mirror_id).first()

    if not mirror.source:
        raise Exception('Mirror {} has no source'.format(mirror.id))

    if not mirror.target:
        raise Exception('Mirror {} has no target'.format(mirror.id))

    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])
    git_remote_source = GitRemote(mirror.source, mirror.is_force_update, mirror.is_prune_mirrors)
    git_remote_target = GitRemote(mirror.target, mirror.is_force_update, mirror.is_prune_mirrors)
    Git.sync_mirror(namespace_path, str(mirror.id), git_remote_source, git_remote_target)

    # 5. Set last_sync date to mirror
    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def sync_push_mirror(self, push_mirror_id: int) -> None:  # pylint: disable=unused-argument
    mirror = PushMirror.query.filter_by(id=push_mirror_id).first()

    if not mirror.source:
        raise Exception('Mirror {} has no source'.format(mirror.id))

    if not mirror.target:
        raise Exception('Mirror {} has no target'.format(mirror.id))

    namespace_path = get_namespace_path(mirror, flask.current_app.config['USER'])
    git_remote_source = GitRemote(mirror.source, mirror.is_force_update, mirror.is_prune_mirrors)
    git_remote_target = GitRemote(mirror.target, mirror.is_force_update, mirror.is_prune_mirrors)
    Git.sync_mirror(namespace_path, str(mirror.id), git_remote_source, git_remote_target)

    # 5. Set last_sync date to mirror
    mirror.last_sync = datetime.datetime.now()
    db.session.add(mirror)
    db.session.commit()


@celery.task(bind=True)
@single_instance(include_args=True)
def delete_pull_mirror(self, pull_mirror_id: int) -> None:  # pylint: disable=unused-argument
    mirror = PullMirror.query.filter_by(id=pull_mirror_id, is_deleted=True).first()
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
def delete_push_mirror(self, push_mirror_id: int) -> None:  # pylint: disable=unused-argument
    mirror = PushMirror.query.filter_by(id=push_mirror_id, is_deleted=True).first()
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
def create_rsa_pair(self, user_id: int) -> None:  # pylint: disable=unused-argument
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
def create_ssh_config(self, user_id: int, host: str, git_url: str) -> None:  # pylint: disable=unused-argument
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise Exception('User {} not found'.format(user_id))

    host_info = GitUri(git_url)
    add_ssh_config(user, flask.current_app.config['USER'], host, host_info)
