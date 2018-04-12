from wtforms import SelectField


class NonValidatingSelectField(SelectField):
    """
    Attempt to make an open ended select field that can accept dynamic
    choices added by the browser.
    """
    def pre_validate(self, form):
        pass