from sqlalchemy import Column, Integer, String, Date
from app.database.postgres import Base

class User(Base):
    __tablename__ = "users"
    username = Column(String, unique=True, nullable=False)
    email = Column(String, primary_key=True, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role =  Column(String, nullable=False, default = "Paziente")

    nome = Column(String, nullable=False)
    cognome = Column(String, nullable=False)
    via = Column(String, nullable=False)
    numero_civico = Column(String, nullable=False)
    citta = Column(String, nullable=False)
    cap = Column(String, nullable=False)
    data_nascita = Column(Date, nullable=False)
    sesso = Column(String, nullable=False)
    medicoAssociato = Column(String, default = None, nullable=True)