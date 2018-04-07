import gitlab
import flask
from flask_babel import gettext
from flask_login import current_user
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, SelectField, BooleanField
from gitlab_tools.models.gitlab_tools import PushMirror
from gitlab_tools.tools.GitRemote import GitRemote

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    project_mirror = StringField(None, [validators.Length(min=1, max=255)])
    note = TextAreaField(None, [validators.Optional()])
    project = SelectField(None, [validators.DataRequired()], coerce=int)

    is_force_update = BooleanField()
    is_prune_mirrors = BooleanField()

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

        gl = gitlab.Gitlab(
            flask.current_app.config['GITLAB_URL'],
            oauth_token=current_user.access_token,
            api_version=flask.current_app.config['GITLAB_API_VERSION']
        )

        gl.auth()

        choices = []
        for project in gl.projects.list():
            choices.append((project.id, '{} ({})'.format(project.name_with_namespace, project.path_with_namespace)))
        self.project.choices = choices

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_mirror_exists = PushMirror.query.filter_by(project_mirror=self.project_mirror.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        if not GitRemote.detect_vcs_type(self.project_mirror.data):
            self.project_mirror.errors.append(
                gettext('Unknown VCS type or detection failed.')
            )
            return False

        return True


class EditForm(NewForm):
    id = HiddenField()

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_mirror_exists = PushMirror.query.filter(PushMirror.project_mirror == self.project_mirror.data, PushMirror.id != self.id.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True
