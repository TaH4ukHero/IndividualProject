import sqlalchemy as sql
from data.db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'
    id = sql.Column(sql.Integer, primary_key=True, autoincrement=True)
    user_id = sql.Column(sql.String, nullable=False)
    attempts = sql.Column(sql.Integer, nullable=False, default=0)
    last_attempts = sql.Column(sql.Integer, nullable=False, default=0)
    most_attempts = sql.Column(sql.Integer, nullable=False, default=0)
    min_attempts = sql.Column(sql.Integer, nullable=False, default=0)
    wins = sql.Column(sql.Integer, nullable=False, default=0)
    loses = sql.Column(sql.Integer, nullable=False, default=0)
