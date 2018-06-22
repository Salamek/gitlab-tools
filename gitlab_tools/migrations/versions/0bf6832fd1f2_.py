"""Create correct sequence

Revision ID: 0bf6832fd1f2
Revises: 3b2efd6da478
Create Date: 2018-06-22 17:56:53.940104

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateSequence, DropSequence


# revision identifiers, used by Alembic.
revision = '0bf6832fd1f2'
down_revision = '3b2efd6da478'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(CreateSequence(Sequence("task_id_sequence")))
    op.execute(CreateSequence(Sequence("taskset_id_sequence")))


def downgrade():
    op.execute(DropSequence(Sequence("task_id_sequence")))
    op.execute(DropSequence(Sequence("taskset_id_sequence")))
