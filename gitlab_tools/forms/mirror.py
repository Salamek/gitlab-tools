import gitlab
import flask
from flask_babel import gettext
from flask_login import current_user
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, SelectField, BooleanField

from gitlab_tools.enums.VcsEnum import VcsEnum
from gitlab_tools.enums.DirectionEnum import DirectionEnum
from gitlab_tools.models.gitlab_tools import Mirror

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    vcs = SelectField(None, [validators.DataRequired()], coerce=int, choices=(
        (VcsEnum.GIT, 'Git'),
        (VcsEnum.BAZAAR, 'Bazaar'),
        (VcsEnum.SVN, 'SVN'),
        (VcsEnum.MERCURIAL, 'Mercurial'),
    ))
    direction = SelectField(None, [validators.DataRequired()], coerce=int, choices=(
        (DirectionEnum.PULL, 'Pull to GitLab'),
        (DirectionEnum.PULL, 'Push from GitLab')
    ))
    project_name = StringField(None, [validators.Length(min=1, max=255)])
    project_mirror = StringField(None, [validators.Length(min=1, max=255)])
    note = TextAreaField(None, [validators.Optional()])
    group = SelectField(None, [validators.DataRequired()], coerce=int)

    is_no_create = BooleanField()
    is_force_create = BooleanField()
    is_no_remote = BooleanField()
    is_issues_enabled = BooleanField()
    is_wall_enabled = BooleanField()
    is_wiki_enabled = BooleanField()
    is_snippets_enabled = BooleanField()
    is_merge_requests_enabled = BooleanField()
    is_public = BooleanField()
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
        for group in gl.groups.list():
            choices.append((group.id, '{} ({})'.format(group.name, group.full_path)))
        self.group.choices = choices

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_name_exists = Mirror.query.filter_by(project_name=self.project_name.data).first()
        if project_name_exists:
            self.project_name.errors.append(
                gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data)
            )
            return False

        project_mirror_exists = Mirror.query.filter_by(project_mirror=self.project_mirror.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True


class EditForm(NewForm):
    id = HiddenField()

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_name_exists = Mirror.query.filter(Mirror.project_name == self.project_name.data, Mirror.id != self.id.data).first()
        if project_name_exists:
            self.project_name.errors.append(gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data))
            return False

        project_mirror_exists = Mirror.query.filter(Mirror.project_mirror == self.project_mirror.data, Mirror.id != self.id.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True
