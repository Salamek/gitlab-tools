import os
import paramiko
from gitlab_tools.tools.crypto import get_remote_server_key


def check_hostname(hostname: str, known_hosts_path: str):
    """
    Get remote_key
    :param hostname: 
    :param known_hosts_path: 
    :return: 
    """
    host_keys = paramiko.hostkeys.HostKeys(known_hosts_path if os.path.isfile(known_hosts_path) else None)
    remote_server_key_lookup = host_keys.lookup(hostname)

    if remote_server_key_lookup:
        key_name, = remote_server_key_lookup
        remote_server_key = remote_server_key_lookup[key_name]
        found = True
    else:
        # Not found, request validation
        remote_server_key = get_remote_server_key(hostname)
        found = False

    return found, remote_server_key


def add_hostname(hostname: str, remote_server_key: paramiko.pkey.PKey, known_hosts_path: str) -> None:
    """
    Add hostname to known_hosts
    :param hostname: 
    :param remote_server_key: 
    :param known_hosts_path: 
    :return: 
    """
    host_keys = paramiko.hostkeys.HostKeys(known_hosts_path if os.path.isfile(known_hosts_path) else None)
    host_keys.add(hostname, remote_server_key.get_name(), remote_server_key)
    host_keys.save(known_hosts_path)
