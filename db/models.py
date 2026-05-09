from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()


class VariantDB(Base):
    __tablename__ = "variants"

    id = Column(Integer, primary_key=True)

    chr = Column(String(10), nullable=False)
    pos = Column(Integer, nullable=False)

    ref = Column(String(50), nullable=False)
    alt = Column(String(50), nullable=False)

    gene = Column(String(30))

    classification = Column(String(200))

    rules = Column(Text)

    unique_key = Column(String(200), unique=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)