from chromadb import Client
from chromadb.config import Settings

def get_chroma_client(persist_directory="./chroma_db"):
    """
    Restituisce un client Chroma aggiornato.
    persist_directory è la cartella dove salvare i dati del DB vettoriale.
    """
    client = Client(Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory=persist_directory
    ))
    return client
