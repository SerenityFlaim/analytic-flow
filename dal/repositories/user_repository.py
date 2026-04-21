from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from dal.models import User

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, email: str, password_hash: str, **kwargs):
        user = User(
            email = email, 
            password_hash = password_hash,
            **kwargs
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email)
        return self.session.execute(query).scalar_one_or_none()
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)
    
    def get_all(self) -> Sequence[User]:
        statement = select(User)
        return self.session.execute(statement).scalars().all()
    
    def update(self, user_id: int, **values) -> None:
        if not values:
            return
        statement = update(User).where(User.user_id == user_id).values(**values)
        self.session.execute(statement)

    def delete(self, user_id: int) -> None:
        statement = delete(User).where(User.user_id == user_id)
        self.session.execute(statement)