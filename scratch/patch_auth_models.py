import os

with open("backend/app/auth/models.py", "r") as f:
    content = f.read()

import_stmt = "from typing import Optional\n"
content = content.replace("from pydantic import BaseModel", import_stmt + "from pydantic import BaseModel")

user_mod = """class User(BaseModel):
    username: str
    role: str
    email: str
    team_id: Optional[str] = None
    shift: str = "morning"  # "morning" | "afternoon" | "night"
"""
content = content.replace("class User(BaseModel):\n    username: str\n    role: str\n    email: str", user_mod)

with open("backend/app/auth/models.py", "w") as f:
    f.write(content)
