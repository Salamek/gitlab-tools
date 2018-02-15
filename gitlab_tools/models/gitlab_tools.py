from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import sys
from werkzeug.security import generate_password_hash, check_password_hash
from gitlab_tools.extensions import db

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class BaseTable(db.Model):
    __abstract__ = True
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.current_timestamp())
    created = db.Column(db.DateTime, default=func.now())


class OAuth2State(BaseTable):
    __tablename__ = 'o_auth2_state'
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(255), unique=True)


class User(BaseTable):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(255))
    access_token = db.Column(db.String(255), unique=True, nullable=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=True)
    expires = db.Column(db.DateTime, default=func.now())
    mirrors = relationship("Mirror", order_by="Mirror.id", backref="user", lazy='dynamic')

    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            if isinstance(self.id, str):
                return self.id
            elif isinstance(self.id, int):
                return self.id
            else:
                return self.id
        except AttributeError:
            raise NotImplementedError('No `id` attribute - override `get_id`')

    def __eq__(self, other):
        """
        Checks the equality of two `UserMixin` objects using `get_id`.
        """
        if isinstance(other, User):
            return self.get_id() == other.get_id()
        return NotImplemented

    def __ne__(self, other):
        """
        Checks the inequality of two `UserMixin` objects using `get_id`.
        """
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    if sys.version_info[0] != 2:  # pragma: no cover
        # Python 3 implicitly set __hash__ to None if we override __eq__
        # We set it back to its default implementation
        __hash__ = object.__hash__


class Mirror(BaseTable):
    __tablename__ = 'mirror'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), index=True)
    vcs = db.Column(db.Integer)
    gitlab_id = db.Column(db.Integer)
    direction = db.Column(db.Integer)
    project_name = db.Column(db.String(255))
    project_mirror = db.Column(db.String(255))
    last_sync = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(255))
    hook_token = db.Column(db.String(255))
    is_no_create = db.Column(db.Boolean)
    is_force_create = db.Column(db.Boolean)
    is_no_remote = db.Column(db.Boolean)
    is_issues_enabled = db.Column(db.Boolean)
    is_wall_enabled = db.Column(db.Boolean)
    is_wiki_enabled = db.Column(db.Boolean)
    is_snippets_enabled = db.Column(db.Boolean)
    is_merge_requests_enabled = db.Column(db.Boolean)
    is_public = db.Column(db.Boolean)
    is_force_update = db.Column(db.Boolean)
    is_prune_mirrors = db.Column(db.Boolean)


class Group(BaseTable):
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    mirrors = relationship("Mirror", order_by="Mirror.id", backref="group", lazy='dynamic')

