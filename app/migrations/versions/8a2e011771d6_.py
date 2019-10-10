"""empty message

Revision ID: 8a2e011771d6
Revises: 46903aca6fe1
Create Date: 2019-10-10 12:17:18.637971

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a2e011771d6'
down_revision = '46903aca6fe1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('custom_attribute_user_storage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('authorising_user_id', sa.Integer(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('value', sa.String(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('uploaded_image_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('custom_attribute_user_storage')
    # ### end Alembic commands ###
