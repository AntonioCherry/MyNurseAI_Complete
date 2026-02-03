from sqlalchemy import Column, Integer, String, LargeBinary
from app.database.postgres import Base

class Doc(Base):
    """
    Classe relativa alla tabella dei documenti memorizzati sul db relazionale
    """
    __tablename__ = "docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    paziente_email = Column(String, nullable=False)
    file_data = Column(LargeBinary, nullable=False)
