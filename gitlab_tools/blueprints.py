# -*- coding: utf-8 -*-

"""All Flask blueprints for the entire application.

All blueprints for all views go here. They shall be imported by the views themselves and by application.py. Blueprint
URL paths are defined here as well.
"""

from flask import Blueprint


def _factory(name: str, partial_module_string: str, url_prefix: str = None) -> Blueprint:
    """Generates blueprint objects for view modules.

    Positional arguments:
    partial_module_string -- string representing a view module without the absolute path (e.g. 'home.index' for
        gitlab-tools.views.home.index).
    url_prefix -- URL prefix passed to the blueprint.

    Returns:
    Blueprint instance for a view module.
    """
    import_name = 'gitlab_tools.views.{}'.format(partial_module_string)
    template_folder = 'templates'
    blueprint = Blueprint(name, import_name, template_folder=template_folder, url_prefix=url_prefix)
    return blueprint


home_index = _factory('home_index', 'home.index')
sign_index = _factory('sign_index', 'sign.index', '/sign')
api_index = _factory('api_index', 'api.index', '/api')

pull_mirror_index = _factory('pull_mirror_index', 'pull_mirror.index', '/pull-mirror')
push_mirror_index = _factory('push_mirror_index', 'push_mirror.index', '/push-mirror')
fingerprint_index = _factory('fingerprint_index', 'fingerprint.index', '/fingerprint')


all_blueprints = (
    home_index,
    sign_index,
    api_index,
    pull_mirror_index,
    fingerprint_index,
    push_mirror_index
)
