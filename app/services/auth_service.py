import hashlib

def hash_password(password: str) -> str:
    """Restituisce l'hash SHA-256 della password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica che la password in chiaro corrisponda all'hash."""
    return hash_password(plain_password) == hashed_password
