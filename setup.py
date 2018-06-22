#!/usr/bin/env python
import os
import re
import sys

from setuptools import setup, find_packages

sys_conf_dir = os.getenv("SYSCONFDIR", "/etc")


def get_requirements(filename: str) -> list:
    return open(os.path.join(filename)).read().splitlines()


def package_files(directory: str) -> list:
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

classes = """
    Development Status :: 4 - Beta
    Intended Audience :: Developers
    Programming Language :: Python
    Programming Language :: Python :: 3
    Programming Language :: Python :: 3.3
    Programming Language :: Python :: 3.4
    Programming Language :: Python :: 3.5
    Programming Language :: Python :: 3.6
    Programming Language :: Python :: Implementation :: CPython
    Programming Language :: Python :: Implementation :: PyPy
    Operating System :: OS Independent
"""
classifiers = [s.strip() for s in classes.split('\n') if s]


install_requires = get_requirements('requirements.txt')
if sys.version_info < (3, 0):
    install_requires.append('futures')


extra_files = [
        'templates/*',
        'migrations/alembic.ini',
        'views/*/templates/*',
        'views/*/templates/*/*',
        'static/*'
]

extra_files.extend(package_files('gitlab_tools/translations'))

extra_files.extend(package_files('gitlab_tools/static/img'))

# Bower components
extra_files.extend(package_files('gitlab_tools/static/node_modules/bootstrap/dist'))
extra_files.extend(package_files('gitlab_tools/static/node_modules/select2/dist'))
extra_files.extend(package_files('gitlab_tools/static/node_modules/font-awesome/css'))
extra_files.extend(package_files('gitlab_tools/static/node_modules/font-awesome/fonts'))
extra_files.extend(package_files('gitlab_tools/static/node_modules/jquery/dist'))


setup(
    name='gitlab-tools',
    version='1.1.3',
    description='GitLab Tools',
    long_description=open('README.md').read(),
    author='Adam Schubert',
    author_email='adam.schubert@sg1-game.net',
    url='https://gitlab.salamek.cz/sadam/gitlab-tools.git',
    license='GPL-3.0',
    classifiers=classifiers,
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=install_requires,
    test_suite="tests",
    tests_require=install_requires,
    package_data={'gitlab_tools': extra_files},
    entry_points={
        'console_scripts': [
            'gitlab-tools = gitlab_tools.__main__:main',
        ],
    },
    data_files=[
        (os.path.join(sys_conf_dir, 'systemd', 'system'), [
            'etc/systemd/system/gitlab-tools.service',
            'etc/systemd/system/gitlab-tools_celerybeat.service',
            'etc/systemd/system/gitlab-tools_celeryworker.service'
        ]),
        (os.path.join(sys_conf_dir, 'gitlab-tools'), [
            'etc/gitlab-tools/config.yml'
        ])
    ]
)
