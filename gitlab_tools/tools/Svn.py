

class Svn:

    @staticmethod
    def fix_url(url: str) -> str:
        # We use unsupported URL formats for SVN, we need to convert that
        if 'svn+http://' in url:
            return url.replace('svn+http://', 'http://')

        if 'svn+https://' in url:
            return url.replace('svn+https://', 'https://')

        return url
