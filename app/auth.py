"""HTTP Basic auth for UI dashboard using admin password hash from config."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from bcrypt import checkpw

from app.core.config import settings

security = HTTPBasic()

USERS = {
    "admin": settings.ADMIN_HASH.encode("utf-8"),
}


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    if credentials.username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    stored_hash = USERS[credentials.username]
    if not checkpw(credentials.password.encode("utf-8"), stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
