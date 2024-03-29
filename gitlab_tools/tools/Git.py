import os
import subprocess  # nosec: B404
import logging
from git import Repo
from gitlab_tools.tools.Svn import Svn
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.GitRemote import GitRemote


class Git:

    @staticmethod
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
            repo.git.reset('--hard')
            repo.git.svn('fetch')
            repo.git.svn('rebase')

            if target:
                #repo.git.config('--bool', 'core.bare', 'true')
                repo.remotes.gitlab.push(refspec='master')
                #repo.git.config('--bool', 'core.bare', 'false')

        else:
            # Everything else
            repo.remotes.origin.fetch(force=source.is_force_update, prune=source.is_prune_mirrors)
            repo.remotes.gitlab.push(
                mirror=True,
                force=target.is_force_update,
                prune=target.is_prune_mirrors
            )

        logging.info('Mirror sync done')

    @staticmethod
    def create_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: GitRemote=None) -> None:

        # 2. Create/pull local repository

        # Check if project clone exists
        project_path = os.path.join(namespace_path, temp_name)
        if os.path.isdir(project_path):
            repo = Repo(project_path)

            # SVN REPO has no origin
            if source.vcs_type not in [VcsEnum.SVN]:
                repo.remotes.origin.set_url(source.url)

            if target:
                repo.remotes.gitlab.set_url(target.url)
        else:
            # Project not found, we can clone
            logging.info('Creating mirror for %s', source.url)

            # 3. Pull
            # 4. Push

            if source.vcs_type == VcsEnum.SVN:
                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'svn', 'clone', Svn.fix_url(source.url), project_path],
                    cwd=namespace_path
                ).communicate()
                repo = Repo(project_path)
            else:
                repo = Repo.clone_from(source.url, project_path, mirror=True)

                if source.vcs_type in [VcsEnum.BAZAAR, VcsEnum.MERCURIAL]:
                    repo.git.gc('--aggressive')

            if target:
                logging.info('Adding GitLab remote to project.')

                repo.create_remote('gitlab', target.url)

        Git.sync_mirror(namespace_path, temp_name, source, target)

        logging.info('All done!')
