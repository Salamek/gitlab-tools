import hashlib
import random
import time
import sys
import os
import pwd
import grp


def random_password() -> str:
    """
    Generates random password with fixed len of 32 characters
    :return: 32 len string
    """
    return hashlib.md5('{}_{}'.format(
        random.randint(0, sys.maxsize),
        round(time.time() * 1000)
    ).encode('UTF-8')).hexdigest()


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
