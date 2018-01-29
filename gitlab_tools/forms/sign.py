from flask_babel import gettext
from wtforms import Form, StringField, PasswordField, validators

from gitlab_tools.models.gitlab_tools import db, User

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class InForm(Form):
    username = StringField(None, [validators.Length(min=5, max=35)])
    password = PasswordField(None, [validators.Length(min=5, max=35)])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False
        user = db.session.query(User).filter(User.username == self.username.data).first()
        # email and password found and match
        if user is None:
            self.username.errors.append(gettext('Username was not found.'))
            return False

        if user.check_password(self.password.data) is False:
            self.password.errors.append(gettext('Wrong password.'))
            return False

        self.user = user
        return True
