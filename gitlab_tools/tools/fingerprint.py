import os
from typing import Tuple
import paramiko
from gitlab_tools.tools.crypto import get_remote_server_key


def get_remote_server_key_for_hostname(hostname: str) -> paramiko.pkey.PKey:
    if ':' in hostname:
        host, port = hostname.split(':')
        return get_remote_server_key(host.replace('[', '').replace(']', ''), int(port))

    return get_remote_server_key(hostname)


def check_hostname(hostname: str, known_hosts_path: str) -> Tuple[bool, paramiko.pkey.PKey]:
    """
    Get remote_key
    :param hostname: Hostname to check
    :param known_hosts_path: Path to known_hosts
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
        remote_server_key = get_remote_server_key_for_hostname(hostname)
        found = False

    return found, remote_server_key


def add_hostname(hostname: str, remote_server_key: paramiko.pkey.PKey, known_hosts_path: str) -> str:
    """
    Add hostname to known_hosts
    :param hostname: str
    :param remote_server_key: paramiko.pkey.PKey
    :param known_hosts_path: str
    :return: str
    """
    host_keys = paramiko.hostkeys.HostKeys(known_hosts_path if os.path.isfile(known_hosts_path) else None)
    hashed_hostname = host_keys.hash_host(hostname)
    host_keys.add(hashed_hostname, remote_server_key.get_name(), remote_server_key)
    #host_keys.add(hostname, remote_server_key.get_name(), remote_server_key)  #!FIXME remove me
    host_keys.save(known_hosts_path)

    return hashed_hostname
