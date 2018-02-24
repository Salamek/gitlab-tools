from wtforms import Form, StringField, validators

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    hostname = StringField(None, [validators.Length(min=1, max=255)])

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        return True
