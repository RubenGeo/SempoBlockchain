"""empty message

Revision ID: 3f51c0edfe02
Revises: e45e3a3b9316
Create Date: 2018-10-03 00:06:40.764224

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f51c0edfe02'
down_revision = 'e45e3a3b9316'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('targeting_survey',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('number_people_household', sa.Integer(), nullable=True),
    sa.Column('number_below_adult_age_household', sa.Integer(), nullable=True),
    sa.Column('number_people_women_household', sa.Integer(), nullable=True),
    sa.Column('number_people_men_household', sa.Integer(), nullable=True),
    sa.Column('number_people_work_household', sa.Integer(), nullable=True),
    sa.Column('disabilities_household', sa.String(), nullable=True),
    sa.Column('long_term_illnesses_household', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('feedback', sa.Column('question', sa.String(), nullable=True))
    op.add_column('user', sa.Column('targeting_survey_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'user', 'targeting_survey', ['targeting_survey_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'user', type_='foreignkey')
    op.drop_column('user', 'targeting_survey_id')
    op.drop_column('feedback', 'question')
    op.drop_table('targeting_survey')
    # ### end Alembic commands ###
