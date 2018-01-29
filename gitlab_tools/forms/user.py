from flask_babel import gettext
from wtforms import Form, StringField, PasswordField, validators, HiddenField, SelectMultipleField

from gitlab_tools.models.gitlab_tools import User, Role

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    username = StringField(None, [validators.Length(min=5, max=35)])
    password = PasswordField(None, [validators.Length(min=5, max=35)])
    password_again = PasswordField(None, [validators.Length(min=5, max=35)])
    roles = SelectMultipleField(None, [validators.DataRequired()], choices=[], coerce=int)

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

        roles = Role.query.all()
        choices = []
        for role in roles:
            choices.append((role.id, role.name))
        self.roles.choices = choices

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        username_exists = User.query.filter_by(username=self.username.data).first()
        if username_exists:
            self.username.errors.append(gettext('Username %(username)s already exists.', username=self.username.data))
            return False

        if self.password.data != self.password_again.data:
            self.password_again.errors.append(gettext('Passwords do not match.'))
            return False

        return True


class EditForm(Form):
    id = HiddenField()
    username = StringField(None, [validators.Length(min=5, max=35)])
    password = PasswordField(None, [])
    password_again = PasswordField(None, [])
    roles = SelectMultipleField(None, [validators.DataRequired()], choices=[], coerce=int)

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)

        roles = Role.query.all()
        choices = []
        for role in roles:
            choices.append((role.id, role.name))
        self.roles.choices = choices

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        username_exists = User.query.filter(User.username == self.username.data, User.id != self.id.data).first()
        if username_exists:
            self.username.errors.append(gettext('Username %(username)s already exists.', username=self.username.data))
            return False

        if self.password.data or self.password_again.data:

            if self.password.data != self.password_again.data:
                self.password_again.errors.append(gettext('Passwords do not match.'))
                return False

        return True
