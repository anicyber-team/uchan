from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from unichan.database import ModelBase


class Report(ModelBase):
    __tablename__ = 'report'

    id = Column(Integer(), primary_key=True)
    post_id = Column(Integer(), ForeignKey('post.id'), nullable=False)
    # post is a backref property
    count = Column(Integer(), nullable=False)
