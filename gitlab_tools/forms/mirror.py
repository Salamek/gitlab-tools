from flask_babel import gettext
from wtforms import Form, StringField, validators, HiddenField, TextAreaField

from gitlab_tools.models.gitlab_tools import Mirror

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    vcs = StringField(None, [validators.Length(min=3, max=255)])
    direction = StringField(None, [validators.Length(min=1, max=60)])
    project_name = StringField(None, [validators.Length(min=1, max=60)])
    project_mirror = StringField(None, [validators.Length(min=1, max=60)])
    note = TextAreaField(None, [validators.Optional()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_name_exists = Mirror.query.filter_by(dns=self.project_name.data).first()
        if project_name_exists:
            self.project_name.errors.append(
                gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data)
            )
            return False

        project_mirror_exists = Mirror.query.filter_by(dns=self.project_mirror.data).first()
        if project_mirror_exists:
            self.project_mirror.errors.append(
                gettext('Project mirror %(project_mirror)s already exists.', project_mirror=self.project_mirror.data)
            )
            return False

        return True


class EditForm(Form):
    id = HiddenField()
    vcs = StringField(None, [validators.Length(min=3, max=255)])
    direction = StringField(None, [validators.Length(min=1, max=60)])
    project_name = StringField(None, [validators.Length(min=1, max=60)])
    project_mirror = StringField(None, [validators.Length(min=1, max=60)])
    note = TextAreaField(None, [validators.Optional()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        project_name_exists = Mirror.query.filter(Mirror.dns == self.project_name.data, Mirror.id != self.id.data).first()
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
