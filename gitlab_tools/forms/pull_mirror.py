
from flask_babel import gettext
from wtforms import Form, StringField, validators, HiddenField, TextAreaField, BooleanField, SelectField
from gitlab_tools.models.gitlab_tools import PullMirror
from gitlab_tools.tools.GitRemote import GitRemote
from cron_descriptor import ExpressionDescriptor, MissingFieldException, FormatException
from gitlab_tools.forms.custom_fields import NonValidatingSelectField
from gitlab_tools.tools.gitlab import check_project_visibility_in_group, VisibilityError, check_project_exists

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class NewForm(Form):
    project_name = StringField(None, [validators.Regexp('^[a-zA-Z0-9_-]+( \w+)*$', message='Project name cannot contain special characters')])
    project_mirror = StringField(None, [validators.Length(min=1, max=255)])
    periodic_sync = StringField(None, [validators.Optional()])
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
    visibility = SelectField(None, [validators.DataRequired()], coerce=str, choices=[
        (PullMirror.VISIBILITY_PRIVATE, gettext('Private')),
        (PullMirror.VISIBILITY_INTERNAL, gettext('Internal')),
        (PullMirror.VISIBILITY_PUBLIC, gettext('Public'))
    ])
    is_force_update = BooleanField()
    is_prune_mirrors = BooleanField()
    is_jobs_enabled = BooleanField()

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

        try:
            check_project_visibility_in_group(self.visibility.data, self.group.data)
        except VisibilityError as e:
            self.visibility.errors.append(
                gettext(str(e))
            )
            return False

        if check_project_exists(self.project_name.data, self.group.data):
            if not self.is_force_create.data:
                self.project_name.errors.append(
                    gettext(
                        'Project with name %(project_name)s already exists in selected group and "Create project in GitLab even if it already exists." is not checked in "Advanced options"',
                        project_name=self.project_name.data
                    )
                )
                return False

        if self.periodic_sync.data:
            try:
                ExpressionDescriptor(self.periodic_sync.data, throw_exception_on_parse_error=True)
            except (MissingFieldException, FormatException):
                self.periodic_sync.errors.append(
                    gettext('Wrong cron expression.')
                )

        return True


class EditForm(NewForm):
    id = HiddenField()

    def validate(self) -> bool:
        rv = Form.validate(self)
        if not rv:
            return False

        current_pull_mirror = PullMirror.query.filter(PullMirror.id == self.id.data).first()

        project_name_exists = PullMirror.query.filter(PullMirror.project_name == self.project_name.data, PullMirror.id != current_pull_mirror.id).first()
        if project_name_exists:
            self.project_name.errors.append(gettext('Project name %(project_name)s already exists.', project_name=self.project_name.data))
            return False

        project_mirror_exists = PullMirror.query.filter(PullMirror.project_mirror == self.project_mirror.data, PullMirror.id != current_pull_mirror.id).first()
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

        try:
            check_project_visibility_in_group(self.visibility.data, self.group.data)
        except VisibilityError as e:
            self.visibility.errors.append(
                gettext(str(e))
            )
            return False

        if check_project_exists(self.project_name.data, self.group.data, current_pull_mirror.project.gitlab_id):
            if not self.is_force_create.data:
                self.project_name.errors.append(
                    gettext(
                        'Project with name %(project_name)s already exists in selected group and "Create project in GitLab even if it already exists." is not checked in "Advanced options"',
                        project_name=self.project_name.data
                    )
                )
                return False

        if self.periodic_sync.data:
            try:
                ExpressionDescriptor(self.periodic_sync.data, throw_exception_on_parse_error=True)
            except (MissingFieldException, FormatException):
                self.periodic_sync.errors.append(
                    gettext('Wrong cron expression.')
                )

        return True
