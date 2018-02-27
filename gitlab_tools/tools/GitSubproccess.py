import os
import subprocess
import logging
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.GitRemote import GitRemote


class GitSubproccess(object):

    @staticmethod
    def sync_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: GitRemote=None):

        # Check if repository storage group directory exists:
        if not os.path.isdir(namespace_path):
            raise Exception('Group storage {} not found, creation failed ?'.format(namespace_path))

        # Check if project clone exists
        project_path = os.path.join(namespace_path, temp_name)
        if not os.path.isdir(project_path):
            raise Exception('Repository storage {} not found, creation failed ?'.format(project_path))

        # Special code for SVN repo mirror
        if source.vcs_type == VcsEnum.SVN:
            subprocess.Popen(['git', 'reset', 'hard'], cwd=project_path).communicate()
            subprocess.Popen(['git', 'svn', 'fetch'], cwd=project_path).communicate()
            subprocess.Popen(['git', 'svn', 'rebase'], cwd=project_path).communicate()

            if not target:
                # repo.git.config('--bool', 'core.bare', 'true')
                subprocess.Popen(['git', 'push', 'gitlab'], cwd=project_path).communicate()
                # repo.git.config('--bool', 'core.bare', 'false')

        else:
            # Everything else
            fetch_command = ['git', 'fetch']
            if source.is_force_update:
                fetch_command.append('--force')
            if source.is_prune_mirrors:
                fetch_command.append('--prune')

            #fetch_command.append('origin')

            push_command = ['git', 'push']
            if target.is_force_update:
                push_command.append('--force')
            if target.is_prune_mirrors:
                push_command.append('--prune')

            push_command.append('gitlab')
            #push_command.append('+refs/heads/*:refs/heads/*')
            #push_command.append('+refs/tags/*:refs/tags/*')

            subprocess.Popen(fetch_command, cwd=project_path).communicate()
            subprocess.Popen(push_command, cwd=project_path).communicate()

        logging.info('Mirror sync done')

    @staticmethod
    def create_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: GitRemote=None) -> None:

        # 2. Create/pull local repository

        # Check if project clone exists
        project_path = os.path.join(namespace_path, temp_name)
        if os.path.isdir(project_path):
            subprocess.Popen(['git', 'remote', 'set-url', 'origin', source.url], cwd=project_path).communicate()
            if target:
                subprocess.Popen(['git', 'remote', 'set-url', 'gitlab', target.url], cwd=project_path).communicate()
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
            else:
                subprocess.Popen(
                    ['git', 'clone', '--mirror', source.url, project_path]
                ).communicate()

                if source.vcs_type in [VcsEnum.BAZAAR, VcsEnum.MERCURIAL]:
                    subprocess.Popen(['git', 'gc', '--aggressive'], cwd=project_path).communicate()

            if target:
                logging.info('Adding GitLab remote to project.')
                subprocess.Popen(['git', 'remote', 'add', 'gitlab', target.url], cwd=project_path).communicate()
                subprocess.Popen(['git', 'config', '--add', 'remote.gitlab.push', '+refs/heads/*:refs/heads/*'], cwd=project_path).communicate()
                subprocess.Popen(['git', 'config', '--add', 'remote.gitlab.push', '+refs/tags/*:refs/tags/*'], cwd=project_path).communicate()
                subprocess.Popen(['git', 'config', 'remote.gitlab.mirror', 'true'], cwd=project_path).communicate()

        GitSubproccess.sync_mirror(namespace_path, temp_name, source, target)

        logging.info('All done!')
