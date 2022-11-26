from flask_babel import gettext
from flask_login import current_user
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, BooleanField
from gitlab_tools.forms.custom_fields import NonValidatingSelectField
from gitlab_tools.models.gitlab_tools import PushMirror
from gitlab_tools.tools.GitRemote import GitRemote

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    project_mirror = StringField(None, [validators.Length(min=1, max=255)])
    note = TextAreaField(None, [validators.Optional()])
    project = NonValidatingSelectField(None, [validators.Optional()], coerce=int, choices=[])

    is_force_update = BooleanField()
    is_prune_mirrors = BooleanField()

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_mirror_exists = PushMirror.query.filter_by(project_mirror=self.project_mirror.data, user=current_user).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        if not GitRemote(self.project_mirror.data).vcs_type:
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

        project_mirror_exists = PushMirror.query.filter(
            PushMirror.project_mirror == self.project_mirror.data,
            PushMirror.id != self.id.data,
            PushMirror.user == current_user
        ).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True
