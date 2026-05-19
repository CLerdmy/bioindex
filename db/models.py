from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from db.session import Base


class VariantDB(Base):

    __tablename__ = "variants"

    id = Column(Integer, primary_key=True)
    classification = Column(String)
    rules = Column(Text)

    chr = Column(String(10), nullable=False)
    pos = Column(Integer, nullable=False)
    ref = Column(String(50), nullable=False)
    alt = Column(String(50), nullable=False) 
    gene = Column(String(30)) 
    

    # FULL DB

    # id = Column(Integer, primary_key=True) 
    # chr = Column(String(10), nullable=False) 
    # pos = Column(Integer, nullable=False) 
    # ref = Column(String(50), nullable=False) 
    # alt = Column(String(50), nullable=False) 
    # gene = Column(String(30)) 
    # db_snp = Column(String(30)) 
    # c_dot = Column(String(80)) 
    # p_dot = Column(String(80)) 
    # transcript = Column(String(100)) 
    # classification = Column(String(200)) 
    # score = Column(Float) 
    # bayes_score = Column(Float) 
    # rules = Column(Text) 
    # unique_key = Column(String(200), unique=True, nullable=False) 
    # created_at = Column(DateTime, default=datetime.now) 
    # updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)