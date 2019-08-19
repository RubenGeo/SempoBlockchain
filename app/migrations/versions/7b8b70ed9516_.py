"""empty message

Revision ID: 7b8b70ed9516
Revises: 2ed5e5423ada
Create Date: 2018-11-10 23:29:52.761619

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b8b70ed9516'
down_revision = '2ed5e5423ada'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('credit_transfer', sa.Column('recipient_blockchain_address_id', sa.Integer(), nullable=True))
    op.add_column('credit_transfer', sa.Column('sender_blockchain_address_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'credit_transfer', 'blockchain_address', ['sender_blockchain_address_id'], ['id'])
    op.create_foreign_key(None, 'credit_transfer', 'blockchain_address', ['recipient_blockchain_address_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'credit_transfer', type_='foreignkey')
    op.drop_constraint(None, 'credit_transfer', type_='foreignkey')
    op.drop_column('credit_transfer', 'sender_blockchain_address_id')
    op.drop_column('credit_transfer', 'recipient_blockchain_address_id')
    # ### end Alembic commands ###
