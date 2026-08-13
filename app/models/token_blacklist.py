"""
app/models/token_blacklist.py

JWTs are stateless by design — issuing one can't be "undone" on the server.
To support a real logout, revoked tokens are recorded here; every protected
request checks this table and rejects tokens that appear in it.

Kept as its own module (not added to models.py) since it's an auth-support
table, not a domain entity like Recruiter/Candidate/Resume.
"""

from sqlalchemy import Column, Integer, String, DateTime, func

from app.db.database import Base


class TokenBlacklist(Base):
    """
    Stores the JTI (or raw token string, for simplicity here) of any access
    token that has been explicitly logged out before its natural expiry.
    """
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<TokenBlacklist id={self.id}>"
