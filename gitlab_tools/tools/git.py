import os
import subprocess
import logging
from git import Repo
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.GitRemote import GitRemote


def sync_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: GitRemote=None):

    # Check if repository storage group directory exists:
    if not os.path.isdir(namespace_path):
        raise Exception('Group storage {} not found, creation failed ?'.format(namespace_path))

    # Check if project clone exists
    project_path = os.path.join(namespace_path, temp_name)
    if not os.path.isdir(project_path):
        raise Exception('Repository storage {} not found, creation failed ?'.format(project_path))

    repo = Repo(project_path)
    # Special code for SVN repo mirror
    if source.vcs_type == VcsEnum.SVN:
        repo.reset(hard=True)  # 'git', 'reset', '--hard'

        subprocess.Popen(
            ['git', 'svn', 'fetch'],
            cwd=project_path
        ).communicate()

        subprocess.Popen(
            ['git', 'svn', 'rebase'],
            cwd=project_path
        ).communicate()

        if not target:
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
        repo.remotes.origin.fetch(force=source.is_force_update, prune=source.is_prune_mirrors)
        repo.remotes.gitlab.push(force=target.is_force_update, prune=target.is_prune_mirrors)

    logging.info('Mirror sync done')


def create_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: GitRemote=None) -> None:

    # 2. Create/pull local repository

    # Check if project clone exists
    project_path = os.path.join(namespace_path, temp_name)
    if os.path.isdir(project_path):
        repo = Repo(project_path)
        repo.remotes.origin.set_url(source.url, mirror='fetch')
        if target:
            repo.remotes.gitlab.set_url(target.url, mirror='push')
    else:
        # Project not found, we can clone
        logging.info('Creating mirror for {}'.format(source.url))

        # 3. Pull
        # 4. Push

        if source.vcs_type == VcsEnum.SVN:
            subprocess.Popen(
                ['git', 'svn', 'clone', source.url, project_path],
                cwd=namespace_path
            ).communicate()
            repo = Repo(project_path)
        else:
            repo = Repo.clone_from(source.url, project_path, mirror=True)

            if source.vcs_type in [VcsEnum.BAZAAR, VcsEnum.MERCURIAL]:
                subprocess.Popen(
                    ['git', 'gc', '--aggressive'],
                    cwd=project_path
                )

        if target:
            logging.info('Adding GitLab remote to project.')

            repo.create_remote('gitlab', target.url, mirror='push')

    sync_mirror(namespace_path, temp_name, source, target)

    logging.info('All done!')
