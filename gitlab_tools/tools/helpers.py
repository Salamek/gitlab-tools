import os
import pwd
import grp
import errno
import paramiko
from gitlab_tools.models.gitlab_tools import User, PullMirror, Mirror
from gitlab_tools.tools.GitUri import GitUri


def get_home_dir(user_name: str) -> str:
    """
    Get home dir by user name
    :param user_name: User name
    :return: Path to homedir
    """
    return os.path.expanduser('~{}'.format(user_name))


def get_namespace_path(mirror: Mirror, user_name: str) -> str:
    """
    Returns path to repository group
    :param mirror: Mirror
    :param user_name: system username
    :return: str
    """
    repository_storage_path = get_repository_storage(user_name)

    if isinstance(mirror, PullMirror):
        return os.path.join(repository_storage_path, str(mirror.user.id), 'pull', str(mirror.group.id))

    return os.path.join(repository_storage_path, str(mirror.user.id), 'push', str(mirror.id))


def get_repository_path(namespace: str, mirror: Mirror) -> str:
    """
    Get repository path
    :param namespace: namespace path
    :param mirror: Mirror
    :return: str
    """
    # Check if project clone exists
    return os.path.join(namespace, str(mirror.id))


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


def get_user_public_key_path(user: User, user_name: str) -> str:
    """
    Returns path for user public key
    :param user: gitlab tools user
    :param user_name: system user name
    :return: str
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'id_rsa_{}.pub'.format(user.id))


def get_user_private_key_path(user: User, user_name: str) -> str:
    """
    Returns path for user private key
    :param user: gitlab tools user
    :param user_name: system user name
    :return: str
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'id_rsa_{}'.format(user.id))


def get_user_known_hosts_path(user: User, user_name: str) -> str:
    """
    Returns path for user known_hosts
    :param user: gitlab tools user
    :param user_name: system user name
    :return: str
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'known_hosts_{}'.format(user.id))


def get_known_hosts_path(user_name: str) -> str:
    """
    Returns path for user known_hosts
    :param user_name: system user name
    :return: str
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'known_hosts')


def get_ssh_config_path(user_name: str) -> str:
    """
    Returns path to ssh config
    :param user_name: str
    :return: str
    """
    ssh_storage = get_ssh_storage(user_name)
    return os.path.join(ssh_storage, 'config')


def convert_url_for_user(url: str, user: User) -> str:
    """
    Converts url hostname of url to user identified type for SSH config
    :param url: Url to convert
    :param user: User to use
    :return: Returns modified URL
    """
    git_remote = GitUri(url)

    return url.replace(git_remote.hostname, '{}_{}'.format(git_remote.hostname, user.id), 1)


def mkdir_p(path: str) -> None:
    """
    Create path recursive
    :param path: Path to create
    :return: None
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def add_ssh_config(user: User, user_name: str, identifier: str, host_info: GitUri) -> None:
    """
    Adds new SSH config host
    :param user: User
    :param user_name: str
    :param identifier: str
    :param host_info: GitUri
    :return: None
    """
    ssh_config_path = get_ssh_config_path(user_name)
    user_known_hosts_path = get_user_known_hosts_path(user, user_name)
    user_private_key_path = get_user_private_key_path(user, user_name)

    ssh_config = paramiko.config.SSHConfig()
    if os.path.isfile(ssh_config_path):
        with open(ssh_config_path, 'r') as f:
            ssh_config.parse(f)
    if identifier not in ssh_config.get_hostnames():
        rows = [
            "Host {}".format(identifier),
            "   HostName {}".format(host_info.hostname),
            "   Port {}".format(host_info.port),
            "   UserKnownHostsFile {}".format(user_known_hosts_path),
            "   IdentitiesOnly yes",
            "   IdentityFile {}".format(user_private_key_path),
            ""
        ]

        with open(ssh_config_path, 'a') as f:
            f.write('\n'.join(rows))
