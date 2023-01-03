#!/usr/bin/env python
import os
import pathlib

from setuptools import setup, find_packages

sys_conf_dir = os.getenv("SYSCONFDIR", "/etc")


current_directory = os.path.dirname(os.path.abspath(__file__))

here = pathlib.Path(__file__).parent.resolve()
os_name = pathlib.Path('/etc/issue').read_text(encoding="utf-8")
long_description = (here / "README.md").read_text(encoding="utf-8")


def package_files(directory: str) -> list:
    paths = []
    for (path, _, filenames) in os.walk(directory):
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


install_requires = [
    'redis==3.5.*',
    'WTForms==2.2.1',
    'psycopg2-binary==2.8.6',
    'pycryptodomex>=3.9.7',
    'python-gitlab>=0.18,<=1.5.*',
    'GitPython>=3.1.14',
    'paramiko>=2.7.2',
    'cron-descriptor==1.2.24',
    'python-dateutil~=2.8.1',
    'markupsafe==2.0.1',

    'Flask-Babel>=0.12.2',
    'Flask-Script~=2.0.6',
    'flask-migrate~=2.6.0',
    'pyyaml~=5.3.1',
    'docopt~=0.6.2',
    'celery~=5.0.0',
    'blinker~=1.4',
    'Flask-Celery-Tools',
    'raven',
]

if os_name.startswith('Debian'):
    # Older versions for debian
    install_requires.extend([
        'flask~=1.1.2',
        'requests~=2.25.1',
        'Flask-Login==0.5.*',
    ])
else:
    install_requires.extend([
        'flask~=2.0.3',
        'requests~=2.27.1',
        'Flask-Login==0.6.*'
    ])

setup(
    name='gitlab-tools',
    version='1.4.4',
    python_requires='>=3.7',
    description='GitLab Tools',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Adam Schubert',
    author_email='adam.schubert@sg1-game.net',
    url='https://gitlab.salamek.cz/sadam/gitlab-tools.git',
    license='GPL-3.0',
    classifiers=classifiers,
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=install_requires,
    test_suite="tests",
    tests_require=[
        'tox'
    ],
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
