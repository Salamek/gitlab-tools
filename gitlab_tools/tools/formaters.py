from gitlab_tools.enums.VcsEnum import VcsEnum

def format_bytes(num: int, suffix: str='B') -> str:
    """
    Format bytes to human readable string
    @param num:
    @param suffix:
    @return:
    """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


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
    else:
        return '<div class="label label-danger">No</div>'


def format_vcs(vcs_id: int) -> str:
    """
    Formats vcs enum to string representation
    :param vcs_id: VcsEnum
    :return: 
    """
    return {
        VcsEnum.GIT: 'Git',
        VcsEnum.SVN: 'SVN',
        VcsEnum.MERCURIAL: 'Mercurial',
        VcsEnum.BAZAAR: 'Bazaar',
    }.get(vcs_id, '?')
