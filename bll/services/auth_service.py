import bcrypt
from typing import Optional
from dal.repositories import UserRepository
from dal import User

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    def register(self, email: str, password: str, name: str, **kwargs) -> User:
        if self.user_repo.get_by_email(email):
            raise ValueError("Пользователь с таким email уже существует.")
        
        hashed_password = self._hash_password(password)

        return self.user_repo.create(
            email = email,
            password_hash = hashed_password,
            name = name,
            **kwargs
        )
    
    def login(self, email: str, password: str) -> User:
        user = self.user_repo.get_by_email(email)
        if not user or not self._verify_password(password, user.password_hash):
            raise ValueError("Неверный email или пароль")
        
        return user
    
