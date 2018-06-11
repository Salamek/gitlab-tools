"""Add visibility field to PullMirror and drops is_public options

Revision ID: 82696705e6df
Revises: 29579044e36c
Create Date: 2018-06-11 17:42:00.647650

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Session = sessionmaker()

Base = declarative_base()


class PullMirror(Base):
    __tablename__ = 'pull_mirror'

    id = sa.Column(sa.Integer, primary_key=True)
    is_public = sa.Column(sa.Boolean())
    visibility = sa.Column(sa.String(255))

# revision identifiers, used by Alembic.
revision = '82696705e6df'
down_revision = '29579044e36c'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    op.add_column('pull_mirror', sa.Column('visibility', sa.String(length=255), nullable=True))

    # Set visibility correctly
    for pull_mirror in session.query(PullMirror):
        pull_mirror.visibility = 'public' if pull_mirror.is_public else 'private'
        session.add(pull_mirror)
    session.commit()

    op.alter_column('pull_mirror', 'visibility', nullable=False)

    op.drop_column('pull_mirror', 'is_public')


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    op.add_column('pull_mirror', sa.Column('is_public', sa.BOOLEAN(), autoincrement=False, nullable=True))
    # Set is_public correctly
    for pull_mirror in session.query(PullMirror):
        pull_mirror.is_public = True if pull_mirror.visibility == 'public' else False
        session.add(pull_mirror)
    session.commit()
    op.drop_column('pull_mirror', 'visibility')
