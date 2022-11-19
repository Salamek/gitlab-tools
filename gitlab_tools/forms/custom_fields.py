from typing import Any
from wtforms import SelectField


class NonValidatingSelectField(SelectField):  # type: ignore
    """
    Attempt to make an open ended select field that can accept dynamic
    choices added by the browser.
    """
    def pre_validate(self, form: Any) -> None:
        pass
