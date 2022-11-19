from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.tools.GitUri import GitUri


class GitRemote(GitUri):
    def __init__(self, url: str, is_force_update: bool = False, is_prune_mirrors: bool = False):
        super().__init__(url)
        self.is_force_update = is_force_update
        self.is_prune_mirrors = is_prune_mirrors

    @property
    def vcs_type(self) -> int:
        """
        Detects VCS type by its URL protocol
        :return: VcsEnum int
        """

        scheme_to_vcs_mapping = {
            'bzr': VcsEnum.BAZAAR,
            'hg': VcsEnum.MERCURIAL,
            'svn': VcsEnum.SVN,
            'ssh': VcsEnum.GIT,
            'http': VcsEnum.GIT,
            'git': VcsEnum.GIT,
        }

        for scheme, vcs in scheme_to_vcs_mapping.items():
            if scheme in self.scheme:
                return vcs

        return VcsEnum.GIT
