"""empty message

Revision ID: 56189bfb2c5f
Revises:
Create Date: 2018-04-04 05:16:24.055254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56189bfb2c5f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('fingerprint',
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('hostname', sa.String(length=255), nullable=True),
    sa.Column('sha256_fingerprint', sa.String(length=255), nullable=True),
    sa.Column('hashed_hostname', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'hashed_hostname', name='_user_id_hashed_hostname_uc')
    )
    op.create_index(op.f('ix_fingerprint_hashed_hostname'), 'fingerprint', ['hashed_hostname'], unique=False)
    op.create_index(op.f('ix_fingerprint_user_id'), 'fingerprint', ['user_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_fingerprint_user_id'), table_name='fingerprint')
    op.drop_index(op.f('ix_fingerprint_hashed_hostname'), table_name='fingerprint')
    op.drop_table('fingerprint')
    # ### end Alembic commands ###
