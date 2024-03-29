import base64
from gitlab_tools.enums.VcsEnum import VcsEnum


def format_bytes(num: int, suffix: str = 'B') -> str:
    """
    Format bytes to human readable string
    @param num:
    @param suffix:
    @return:
    """
    temp_num = float(num)
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(temp_num) < 1024:
            return "%3.1f %s%s" % (temp_num, unit, suffix)
        temp_num /= 1024
    return "%.1f%s%s" % (temp_num, 'Yi', suffix)


def fix_url(url: str) -> str:
    """
    Fixes url
    :param url:
    :return:
    """
    if not url.startswith('http'):
        url = 'http://{}'.format(url)
    return url


def format_boolean(bool_to_format: bool) -> str:
    """
    Formats boolean
    :param bool_to_format:
    :return:
    """
    if bool_to_format:
        return '<div class="label label-success">Yes</div>'

    return '<div class="label label-danger">No</div>'


def format_vcs(vcs_id: int) -> str:
    """
    Formats vcs enum to string representation
    :param vcs_id: VcsEnum
    :return: str
    """
    return {
        VcsEnum.GIT: 'Git',
        VcsEnum.SVN: 'SVN',
        VcsEnum.MERCURIAL: 'Mercurial',
        VcsEnum.BAZAAR: 'Bazaar',
    }.get(vcs_id, '?')


def format_md5_fingerprint(fingerprint: bytes) -> str:
    """
    Formats md5 fingerprint
    :param fingerprint: fingerprint to format
    :return: formated fingerprint
    """
    fingerprint_hex = fingerprint.hex()
    return ':'.join(a + b for a, b in zip(fingerprint_hex[::2], fingerprint_hex[1::2]))


def format_sha256_fingerprint(fingerprint: bytes) -> str:
    """
    Formats sha256 fingerprint
    :param fingerprint: fingerprint to format
    :return: formated fingerprint
    """
    return base64.b64encode(fingerprint).decode().rstrip('=')
