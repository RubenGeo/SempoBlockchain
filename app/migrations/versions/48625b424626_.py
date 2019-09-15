"""empty message

Revision ID: 48625b424626
Revises: 6024fbc5d9b4
Create Date: 2019-09-15 11:24:37.332532

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '48625b424626'
down_revision = '6024fbc5d9b4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('token', sa.Column('decimals', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('token', 'decimals')
    # ### end Alembic commands ###