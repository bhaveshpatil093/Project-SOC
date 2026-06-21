import bcrypt
from typing import Optional
from pydantic import BaseModel


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

class User(BaseModel):
    username: str
    role: str
    email: str
    team_id: Optional[str] = None
    shift: str = "morning"  # "morning" | "afternoon" | "night"


class UserInDB(User):
    hashed_password: str

# Hardcoded ISRO internal DB purely for architectural demonstration bounding cleanly
USERS_DB = {
    "admin": UserInDB(
        username="admin",
        role="admin",
        email="admin@istrac.isro.gov.in",
        hashed_password=hash_password("admin123")
    ),
    "analyst": UserInDB(
        username="analyst",
        role="analyst",
        email="analyst@istrac.isro.gov.in",
        hashed_password=hash_password("analyst123")
    ),
    "viewer": UserInDB(
        username="viewer",
        role="viewer",
        email="viewer@istrac.isro.gov.in",
        hashed_password=hash_password("viewer123")
    ),
}
