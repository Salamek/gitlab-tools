# -*- coding: utf-8 -*-

from flask import jsonify, request, url_for, render_template

from gitlab_tools.blueprints import api_index


__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


@api_index.route('/sync/<int:mirror_id>', methods=['POST'])
def log_blocks(mirror_id: int):

    return jsonify({}), 200
