import os
import subprocess  # nosec: B404
import logging
from typing import Optional
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.GitRemote import GitRemote


class GitSubprocess:

    @staticmethod
    def sync_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: Optional[GitRemote] = None) -> None:

        # Check if repository storage group directory exists:
        if not os.path.isdir(namespace_path):
            raise Exception('Group storage {} not found, creation failed ?'.format(namespace_path))

        # Check if project clone exists
        project_path = os.path.join(namespace_path, temp_name)
        if not os.path.isdir(project_path):
            raise Exception('Repository storage {} not found, creation failed ?'.format(project_path))

        # Special code for SVN repo mirror
        if source.vcs_type == VcsEnum.SVN:
            subprocess.Popen(['git', 'reset', 'hard'], cwd=project_path).communicate()  # nosec: B607, B603
            subprocess.Popen(['git', 'svn', 'fetch'], cwd=project_path).communicate()  # nosec: B607, B603
            subprocess.Popen(['git', 'svn', 'rebase'], cwd=project_path).communicate()  # nosec: B607, B603

            if not target:
                # repo.git.config('--bool', 'core.bare', 'true')
                subprocess.Popen(['git', 'push', 'gitlab'], cwd=project_path).communicate()  # nosec: B607, B603
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
            if target:
                if target.is_force_update:
                    push_command.append('--force')
                if target.is_prune_mirrors:
                    push_command.append('--prune')

            push_command.append('gitlab')
            #push_command.append('+refs/heads/*:refs/heads/*')
            #push_command.append('+refs/tags/*:refs/tags/*')

            subprocess.Popen(fetch_command, cwd=project_path).communicate()  # nosec: B607, B603
            subprocess.Popen(push_command, cwd=project_path).communicate()  # nosec: B607, B603

        logging.info('Mirror sync done')

    @staticmethod
    def create_mirror(namespace_path: str, temp_name: str, source: GitRemote, target: Optional[GitRemote] = None) -> None:

        # 2. Create/pull local repository

        # Check if project clone exists
        project_path = os.path.join(namespace_path, temp_name)
        if os.path.isdir(project_path):
            subprocess.Popen(  # nosec: B607, B603
                ['git', 'remote', 'set-url', 'origin', source.url]
                , cwd=project_path
            ).communicate()
            if target:
                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'remote', 'set-url', 'gitlab', target.url],
                    cwd=project_path
                ).communicate()
        else:
            # Project not found, we can clone
            logging.info('Creating mirror for %s', source.url)

            # 3. Pull
            # 4. Push

            if source.vcs_type == VcsEnum.SVN:
                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'svn', 'clone', source.url, project_path],
                    cwd=namespace_path
                ).communicate()
            else:
                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'clone', '--mirror', source.url, project_path]
                ).communicate()

                if source.vcs_type in [VcsEnum.BAZAAR, VcsEnum.MERCURIAL]:
                    subprocess.Popen(['git', 'gc', '--aggressive'], cwd=project_path).communicate()  # nosec: B607, B603

            if target:
                logging.info('Adding GitLab remote to project.')
                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'remote', 'add', 'gitlab', target.url],
                    cwd=project_path
                ).communicate()

                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'config', '--add', 'remote.gitlab.push', '+refs/heads/*:refs/heads/*'],
                    cwd=project_path
                ).communicate()

                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'config', '--add', 'remote.gitlab.push', '+refs/tags/*:refs/tags/*'],
                    cwd=project_path
                ).communicate()

                subprocess.Popen(  # nosec: B607, B603
                    ['git', 'config', 'remote.gitlab.mirror', 'true'],
                    cwd=project_path
                ).communicate()

        GitSubprocess.sync_mirror(namespace_path, temp_name, source, target)

        logging.info('All done!')
