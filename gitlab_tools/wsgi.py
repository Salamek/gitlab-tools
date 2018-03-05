"""
Bootstrap for use in uwsgi and so
"""

from gitlab_tools.application import create_app, get_config

config = get_config('gitlab_tools.config.Production')
app = create_app(config)
