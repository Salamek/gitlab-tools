from flask_babel import gettext
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, BooleanField
from gitlab_tools.models.gitlab_tools import PullMirror
from gitlab_tools.tools.GitRemote import GitRemote
from gitlab_tools.forms.custom_fields import NonValidatingSelectField

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    project_name = StringField(None, [validators.Length(min=1, max=255)])
    project_mirror = StringField(None, [validators.Length(min=1, max=255)])
    note = TextAreaField(None, [validators.Optional()])
    group = NonValidatingSelectField(None, [validators.Optional()], coerce=int, choices=[])

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

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_name_exists = PullMirror.query.filter_by(project_name=self.project_name.data).first()
        if project_name_exists:
            self.project_name.errors.append(
                gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data)
            )
            return False

        project_mirror_exists = PullMirror.query.filter_by(project_mirror=self.project_mirror.data).first()
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

        project_name_exists = PullMirror.query.filter(PullMirror.project_name == self.project_name.data, PullMirror.id != self.id.data).first()
        if project_name_exists:
            self.project_name.errors.append(gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data))
            return False

        project_mirror_exists = PullMirror.query.filter(PullMirror.project_mirror == self.project_mirror.data, PullMirror.id != self.id.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True
