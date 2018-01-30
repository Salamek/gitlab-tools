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


mirror_group_association_table = db.Table(
    'mirror_group_association',
    BaseTable.metadata,
    db.Column('mirror_id', db.Integer, db.ForeignKey('mirror.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)


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
    vcs = db.Column(db.Integer)
    direction = db.Column(db.Integer)
    project_name = db.Column(db.String(255))
    project_mirror = db.Column(db.String(255))
    last_sync = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(255))
    hook_token = db.Column(db.String(255))

    groups = relationship(
        "Group",
        order_by="Group.updated.desc()",
        lazy="dynamic",
        secondary=mirror_group_association_table,
        back_populates="mirrors")


class Group(BaseTable):
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.Text)

    mirrors = relationship(
        "Mirror",
        lazy="dynamic",
        secondary=mirror_group_association_table,
        back_populates="groups")
