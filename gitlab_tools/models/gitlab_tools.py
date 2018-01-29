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


user_role_association_table = db.Table(
    'user_role_association',
    BaseTable.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'))
)

mirror_group_association_table = db.Table(
    'mirror_group_association',
    BaseTable.metadata,
    db.Column('mirror_id', db.Integer, db.ForeignKey('mirror.id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)


class User(BaseTable):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    roles = relationship(
        "Role",
        secondary=user_role_association_table,
        back_populates="users")

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

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


class Role(BaseTable):
    GUEST = 1
    ADMIN = 2
    CUSTOMER = 3
    MAINTENANCE = 4

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    users = relationship(
        "User",
        secondary=user_role_association_table,
        back_populates="roles")

    def __repr__(self) -> str:
        return self.name


class Mirror(BaseTable):
    VCS_GIT = 1
    VCS_BAZAAR = 2
    VCS_SVN = 3

    DIRECTION_PUSH = 1
    DIRECTION_PULL = 2

    __tablename__ = 'mirror'
    id = db.Column(db.Integer, primary_key=True)
    vcs = db.Column(db.Integer)
    direction = db.Column(db.Integer)
    project_name = db.Column(db.String(255))
    project_mirror = db.Column(db.DateTime)
    last_sync = db.Column(db.DateTime)
    note = db.Column(db.String(255))

    groups = relationship(
        "Group",
        order_by="Group.updated.desc()",
        lazy="dynamic",
        secondary=mirror_group_association_table,
        back_populates="mirrors")


class Group(BaseTable):
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)

    mirrors = relationship(
        "Mirror",
        lazy="dynamic",
        secondary=mirror_group_association_table,
        back_populates="groups")
