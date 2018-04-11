import re
import urllib.parse
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from typing import Union


class GitRemote(object):
    def __init__(self, url: str, is_force_update: bool=False, is_prune_mirrors: bool=False):
        self.vcs_type = GitRemote.detect_vcs_type(url)
        self.vcs_protocol = GitRemote.detect_vcs_protocol(url)
        self.hostname = GitRemote.get_url_hostname(url)

        self.url = url
        self.is_force_update = is_force_update
        self.is_prune_mirrors = is_prune_mirrors

    @staticmethod
    def detect_vcs_type(vcs_url: str) -> Union[int, None]:
        """
        Detects VCS type by its URL protocol
        :param vcs_url: URL to detect
        :return: VcsEnum int
        """
        parsed_url = urllib.parse.urlparse(vcs_url)
        if 'bzr' in parsed_url.scheme:
            return VcsEnum.BAZAAR

        if 'hg' in parsed_url.scheme:
            return VcsEnum.MERCURIAL

        if 'svn' in parsed_url.scheme:
            return VcsEnum.SVN

        # We got here... so it must be Git Right ? Lets validate that also...
        if 'ssh' in parsed_url.scheme:
            return VcsEnum.GIT

        if 'http' in parsed_url.scheme:
            return VcsEnum.GIT

        if 'git' in parsed_url.scheme:
            return VcsEnum.GIT

        if not parsed_url.scheme:
            return VcsEnum.GIT

        return None

    @staticmethod
    def detect_vcs_protocol(vcs_url: str) -> int:
        """
            Detects VCS protocol by its URL protocol
            :param vcs_url: URL to detect
            :return: VcsEnum int
            """
        parsed_url = urllib.parse.urlparse(vcs_url)
        if 'bzr' in parsed_url.scheme:
            return ProtocolEnum.HTTPS if 'https' in parsed_url.scheme else ProtocolEnum.HTTP

        if 'hg' in parsed_url.scheme:
            return ProtocolEnum.HTTPS if 'https' in parsed_url.scheme else ProtocolEnum.HTTP

        if 'svn' in parsed_url.scheme:
            return ProtocolEnum.HTTPS if 'https' in parsed_url.scheme else ProtocolEnum.HTTP

        if 'ssh' in parsed_url.scheme:
            return ProtocolEnum.SSH

        if 'http' in parsed_url.scheme:
            return ProtocolEnum.HTTPS if 'https' in parsed_url.scheme else ProtocolEnum.HTTP

        if 'git' in parsed_url.scheme:
            return ProtocolEnum.SSH

        if not parsed_url.scheme:
            return ProtocolEnum.SSH

        return ProtocolEnum.SSH

    @staticmethod
    def parse_scp_like_url(url: str) -> Union[dict, None]:
        """
        Parses SCP like URL
        :param url: Url to parse
        :return: parset chunks
        """
        compiled_re = re.compile(r'(?P<username>.+)@(?P<hostname>.+):(?P<path>.+).git')
        result = compiled_re.search(url)
        if not result:
            return None

        return {
            'username': result.group('username'),
            'hostname': result.group('hostname'),
            'path': result.group('path')
        }

    @staticmethod
    def get_url_hostname(url: str) -> str:
        """
        Get only hostname from URL
        :param url: url to parse
        :return: hostname
        """
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.hostname:
            hostname = parsed_url.hostname
        else:
            parsed_scp_like = GitRemote.parse_scp_like_url(url)
            hostname = parsed_scp_like['hostname']

        if not hostname:
            raise Exception('Failed to detect hostname')

        return hostname
