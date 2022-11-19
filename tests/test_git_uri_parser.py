import pytest
from gitlab_tools.tools.GitUri import GitUri


def test_be_constructed_with() -> None:
    result = GitUri('ssh://git@github.com:22/asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'



def test_git_uri_with_scheme_user_port_path() -> None:
    result = GitUri('ssh://git@github.com:22/asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'


def test_git_uri_with_scheme_user_password_port_path() -> None:
    result = GitUri('ssh://git:password@github.com:22/asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == 'password'
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git:password@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git:password@github.com:/asdf/asdf.git'


def test_git_uri_with_scheme_user_path_with_leading_slash() -> None:
    result = GitUri('ssh://git@github.com:/asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'


def test_git_uri_with_scheme_user_path() -> None:
    result = GitUri('ssh://git@github.com:asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'


def test_git_uri_with_user_path() -> None:
    result = GitUri('git@github.com:asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'


def test_uri_with_hostname_port_path() -> None:
    result = GitUri('github.com:2222/sdfsdf.git')
    assert result.scheme == 'ssh'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 2222
    assert result.path == '/sdfsdf.git'
    assert result.url == 'ssh://github.com:2222/sdfsdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://github.com:2222/sdfsdf.git'


def test_uri_with_hostname_port() -> None:
    result = GitUri('github.com:2222')
    assert result.scheme == 'ssh'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 2222
    assert result.path == '/'
    assert result.url == 'ssh://github.com:2222/'
    assert result.build_url(ignore_default_port=True) == 'ssh://github.com:2222/'


def test_uri_with_hostname() -> None:
    result = GitUri('github.com')
    assert result.scheme == 'ssh'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/'
    assert result.url == 'ssh://github.com:22/'
    assert result.build_url(ignore_default_port=True) == 'ssh://github.com:/'


def test_git_uri_with_scheme_user_path_with_leading_slash_no_coma() -> None:
    result = GitUri('ssh://git@github.com/asdf/asdf.git')
    assert result.scheme == 'ssh'
    assert result.username == 'git'
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 22
    assert result.path == '/asdf/asdf.git'
    assert result.url == 'ssh://git@github.com:22/asdf/asdf.git'
    assert result.build_url(ignore_default_port=True) == 'ssh://git@github.com:/asdf/asdf.git'


def test_https_uri_with_scheme_path() -> None:
    result = GitUri('https://github.com/Salamek/qiosk.git')
    assert result.scheme == 'https'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 443
    assert result.path == '/Salamek/qiosk.git'
    assert result.url == 'https://github.com:443/Salamek/qiosk.git'
    assert result.build_url(ignore_default_port=True) == 'https://github.com/Salamek/qiosk.git'


def test_http_uri_with_scheme_path() -> None:
    result = GitUri('http://github.com/Salamek/qiosk.git')
    assert result.scheme == 'http'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 80
    assert result.path == '/Salamek/qiosk.git'
    assert result.url == 'http://github.com:80/Salamek/qiosk.git'
    assert result.build_url(ignore_default_port=True) == 'http://github.com/Salamek/qiosk.git'


def test_http_uri_with_scheme_path_port() -> None:
    result = GitUri('http://github.com:8080/Salamek/qiosk.git')
    assert result.scheme == 'http'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 8080
    assert result.path == '/Salamek/qiosk.git'
    assert result.url == 'http://github.com:8080/Salamek/qiosk.git'
    assert result.build_url(ignore_default_port=True) == 'http://github.com:8080/Salamek/qiosk.git'


def test_https_uri_with_scheme_path_port() -> None:
    result = GitUri('https://github.com:8443/Salamek/qiosk.git')
    assert result.scheme == 'https'
    assert result.username == None
    assert result.password == None
    assert result.hostname == 'github.com'
    assert result.port == 8443
    assert result.path == '/Salamek/qiosk.git'
    assert result.url == 'https://github.com:8443/Salamek/qiosk.git'
    assert result.build_url(ignore_default_port=True) == 'https://github.com:8443/Salamek/qiosk.git'