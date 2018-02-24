import gitlab
import flask
from flask_babel import gettext
from flask_login import current_user
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, SelectField, BooleanField

from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.enums.ProtocolEnum import ProtocolEnum
from gitlab_tools.models.gitlab_tools import PullMirror
from gitlab_tools.tools.helpers import detect_vcs_type

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    hostname = StringField(None, [validators.Length(min=1, max=255)])

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        return True
