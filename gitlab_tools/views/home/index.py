import flask

from gitlab_tools.models.gitlab_tools import Mirror
from gitlab_tools.blueprints import home_index

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@home_index.route('/', methods=['GET'])
def get_home():
    mirrors = Mirror.query.count()
    return flask.render_template('home.index.home.html', mirrors=mirrors)
