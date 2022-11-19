import re
import urllib.parse
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum


class GitUri:

    # Mapping of scheme to (default_port, ProtocolEnum)
    scheme_to_info = {
        'ssh': (22, ProtocolEnum.SSH),
        'git': (22, ProtocolEnum.SSH),
        'https': (443, ProtocolEnum.HTTPS),
        'http': (80, ProtocolEnum.HTTP)
    }

    def __init__(self, uri: str, default_scheme: str = 'ssh'):
        self.default_scheme = default_scheme

        if not re.match(r'^\S+://', uri):
            # URI has no scheme, prepend one
            uri = '{}://{}'.format(self.default_scheme, uri)

        parsed = urllib.parse.urlparse(uri)
        default_port, protocol = self._detect_scheme_info(parsed.scheme)

        self.default_port = default_port
        self.scheme = parsed.scheme
        self.username = parsed.username
        self.password = parsed.password
        self.hostname = parsed.hostname
        self.path = parsed.path
        self.protocol = protocol

        try:
            self.port = parsed.port or self.default_port
        except ValueError:
            self.port = self.default_port

        # Check if we have single : in netloc, that means no port was provided but : was still there (GIT format)
        # Remove login info
        if '@' in parsed.netloc:
            _, netloc = parsed.netloc.split('@')
        else:
            netloc = parsed.netloc

        if ':' in netloc:
            hostname, path_prefix = netloc.split(':')
            if not path_prefix.isnumeric():
                self.path = path_prefix + parsed.path

        # Check that path starts with /
        if not self.path.startswith('/'):
            self.path = '/{}'.format(self.path)

    def _detect_scheme_info(self, scheme: str):
        exact_match = self.scheme_to_info.get(scheme)
        if exact_match:
            return exact_match

        for key, value in self.scheme_to_info.items():
            if key in scheme:
                return value

    @property
    def url(self):
        return self.build_url()

    def build_url(self, ignore_default_port: bool = False) -> str:
        hostname_parts = []
        if self.username:
            hostname_parts.append(self.username)

        if self.password:
            hostname_parts.append(':')
            hostname_parts.append(self.password)

        if self.username:
            hostname_parts.append('@')

        hostname_parts.append(self.hostname)

        port = self.port
        if self.port == self.default_port and ignore_default_port:
            port = ''

        return '{}://{}{}{}{}'.format(
            self.scheme,
            ''.join(hostname_parts),
            ':' if self.protocol == ProtocolEnum.SSH or port else '',
            port,
            self.path
        )

    def __str__(self) -> str:
        return self.url
