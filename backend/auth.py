
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from database import get_db
import sqlite3

security = HTTPBasic()

def verify_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify user credentials"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT email, password FROM users WHERE email = ?",
        (credentials.username,)
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    if user[1] != credentials.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username  # Return email
