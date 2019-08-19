"""empty message

Revision ID: 7da32d18103f
Revises: b9ef03983336
Create Date: 2018-08-13 11:29:58.317323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7da32d18103f'
down_revision = 'b9ef03983336'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transfer_account', sa.Column('_location', sa.String(), nullable=True))
    op.add_column('transfer_account', sa.Column('_phone', sa.String(), nullable=True))
    op.drop_column('transfer_account', 'location')
    op.drop_column('transfer_account', 'phone')
    op.add_column('user', sa.Column('_phone', sa.String(), nullable=True))
    op.drop_column('user', 'phone')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('phone', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('user', '_phone')
    op.add_column('transfer_account', sa.Column('phone', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('transfer_account', sa.Column('location', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('transfer_account', '_phone')
    op.drop_column('transfer_account', '_location')
    # ### end Alembic commands ###
