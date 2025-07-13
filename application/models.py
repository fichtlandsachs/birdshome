from sqlalchemy import String, Column
from sqlalchemy.ext.declarative import declarative_base

from application import db

Base = declarative_base()


class Appconfig(db.Model):
    __tablename__ = "config"
    config_area = Column(String(255), primary_key=True, index=True, unique=False, nullable=False)
    config_key = Column(String(255), primary_key=True, index=True, unique=False, nullable=False)
    config_value = Column(String, primary_key=False, index=False, unique=False, nullable=True)
