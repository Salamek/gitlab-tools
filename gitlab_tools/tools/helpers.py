import hashlib
import random
import socket
import paramiko
import time
import sys
import os
import pwd
import grp
import re
import urllib.parse
from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from gitlab_tools.models.gitlab_tools import User
from typing import Union


def get_home_dir(user_name: str) -> str:
    """
    Get home dir by user name
    :param user_name: User name
    :return: Path to homedir
    """
    return os.path.expanduser('~{}'.format(user_name))


def get_ssh_storage(user_name: str) -> str:
    """
    Gets user default ssh storage
    :param user_name: User name
    :return: path to ssh storage
    """
    return os.path.join(get_home_dir(user_name), '.ssh')


def get_repository_storage(user_name: str) -> str:
    """
    Gets user repository storage
    :param user_name: user name
    :return: path to repository storage
    """
    return os.path.join(get_home_dir(user_name), 'repositories')


def get_user_group_id(user_name: str) -> int:
    """
    Returns Default user group id
    :param user_name: User name
    :return: group id
    """
    return pwd.getpwnam(user_name).pw_gid


def get_group_name(group_id: int) -> str:
    """
    Returns group name by ID
    :param group_id: Group id
    :return: Group name
    """
    return grp.getgrgid(group_id).gr_name


def get_user_id(user_name: str) -> int:
    """
    Returns user ID
    :param user_name: User name 
    :return: User ID
    """
    return pwd.getpwnam(user_name).pw_uid


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


def parse_scp_like_url(url: str) -> dict:
    """
    Parses SCP like URL
    :param url: Url to parse
    :return: parset chunks
    """
    compiled_re = re.compile(r'(?P<username>.+)@(?P<hostname>.+):(?P<path>.+).git')
    result = compiled_re.search(url)
    return {
        'username': result.group('username'),
        'hostname': result.group('hostname'),
        'path': result.group('path')
    }


def get_user_public_key_path(user: User, user_name: str) -> str:
    """
    Returns path for user public key
    :param user: gitlab tools user
    :param user_name: system user name
    :return: 
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'id_rsa_{}.pub'.format(user.id))


def get_user_private_key_path(user: User, user_name: str) -> str:
    """
    Returns path for user private key
    :param user: gitlab tools user
    :param user_name: system user name
    :return: 
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'id_rsa_{}'.format(user.id))


def get_user_know_hosts_path(user: User, user_name: str) -> str:
    """
    Returns path for user know_hosts
    :param user: gitlab tools user
    :param user_name: system user name
    :return: 
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'know_hosts_{}'.format(user.id))


def convert_url_for_user(url: str, user: User, user_name: str) -> str:
    return url