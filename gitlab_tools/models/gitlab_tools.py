import sys
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from gitlab_tools.extensions import db

__author__ = "Adam Schubert"
__date__ = "$26.7.2017 19:33:05$"


class BaseTable(db.Model):
    __abstract__ = True
    updated = db.Column(db.DateTime, default=func.now(), onupdate=func.current_timestamp())
    created = db.Column(db.DateTime, default=func.now())


class Mirror(BaseTable):
    __abstract__ = True

    @declared_attr
    def user_id(self):
        return db.Column(db.Integer, db.ForeignKey('user.id'), index=True)

    @declared_attr
    def project_id(self):
        return db.Column(db.Integer, db.ForeignKey('project.id'), index=True)

    source = db.Column(db.String(255), nullable=True)
    target = db.Column(db.String(255), nullable=True)
    foreign_vcs_type = db.Column(db.Integer)
    last_sync = db.Column(db.DateTime, nullable=True)
    note = db.Column(db.String(255))
    hook_token = db.Column(db.String(255))
    is_force_update = db.Column(db.Boolean)
    is_prune_mirrors = db.Column(db.Boolean)
    is_deleted = db.Column(db.Boolean)


class OAuth2State(BaseTable):
    __tablename__ = 'o_auth2_state'
    id = db.Column(db.Integer, primary_key=True)
    state = db.Column(db.String(255), unique=True)


class User(BaseTable):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True, nullable=False)
    gitlab_deploy_key_id = db.Column(db.Integer, unique=True, nullable=True)
    is_rsa_pair_set = db.Column(db.Boolean)
    name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(255))
    access_token = db.Column(db.String(255), unique=True, nullable=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=True)
    expires = db.Column(db.DateTime, default=func.now())
    pull_mirrors = relationship("PullMirror", order_by="PullMirror.id", backref="user", lazy='dynamic')
    push_mirrors = relationship("PushMirror", order_by="PushMirror.id", backref="user", lazy='dynamic')

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


class Fingerprint(BaseTable):
    __tablename__ = 'fingerprint'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'hashed_hostname', name='_user_id_hashed_hostname_uc'),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    hostname = db.Column(db.String(255))
    sha256_fingerprint = db.Column(db.String(255))
    hashed_hostname = db.Column(db.String(255), index=True)


class PullMirror(Mirror):
    __tablename__ = 'pull_mirror'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), index=True)
    periodic_task_id = db.Column(db.Integer, db.ForeignKey('periodic_task.id'), index=True, nullable=True)
    periodic_sync = db.Column(db.String(255), nullable=True)
    project_name = db.Column(db.String(255))
    project_mirror = db.Column(db.String(255))
    is_no_create = db.Column(db.Boolean)
    is_force_create = db.Column(db.Boolean)
    is_no_remote = db.Column(db.Boolean)
    is_issues_enabled = db.Column(db.Boolean)
    is_wall_enabled = db.Column(db.Boolean)
    is_wiki_enabled = db.Column(db.Boolean)
    is_snippets_enabled = db.Column(db.Boolean)
    is_merge_requests_enabled = db.Column(db.Boolean)
    is_public = db.Column(db.Boolean)


class PushMirror(Mirror):
    __tablename__ = 'push_mirror'
    id = db.Column(db.Integer, primary_key=True)
    project_mirror = db.Column(db.String(255))


class Project(BaseTable):
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    name_with_namespace = db.Column(db.String(255))
    web_url = db.Column(db.String(255))
    push_mirrors = relationship("PushMirror", order_by="PushMirror.id", backref="project", lazy='dynamic')
    pull_mirrors = relationship("PullMirror", order_by="PullMirror.id", backref="project", lazy='dynamic')


class Group(BaseTable):
    __tablename__ = 'group'

    id = db.Column(db.Integer, primary_key=True)
    gitlab_id = db.Column(db.Integer, unique=True)
    name = db.Column(db.String(255))
    pull_mirrors = relationship("PullMirror", order_by="PullMirror.id", backref="group", lazy='dynamic')

