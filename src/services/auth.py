from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, User
from src.schemas.user import Response
from .environment import environment


class Auth:
    __ALGORITHM = 'HS256'
    __pwd_context = CryptContext(['bcrypt'], deprecated='auto')

    def __init__(self) -> None:
        self.__SECRET = environment('SECRET')

    def verify_password(
        self,
        plain_password: str,
        hashed_password: str
    ) -> bool:
        return self.__pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.__pwd_context.hash(password)

    oauth2_scheme = OAuth2PasswordBearer('api/auth/login')

    async def create_token(
        self,
        email: str,
        refresh_token: bool = False,
        expires_delta: Optional[float] = None
    ) -> str:
        payload = {
            'sub': email,
            'scope': 'refresh_token' if refresh_token else 'access_token',
            **{key: datetime.now(UTC) for key in ('iat', 'exp')},
        }

        if expires_delta:
            payload['exp'] += timedelta(seconds=expires_delta)
        else:
            payload['exp'] += timedelta(minutes=15)

        return jwt.encode(payload, self.__SECRET, self.__ALGORITHM)

    async def decode_refresh_token(self, refresh_token: str) -> str:
        try:
            payload = jwt.decode(
                refresh_token,
                self.__SECRET,
                [self.__ALGORITHM],
            )

            if payload['scope'] == 'refresh_token':
                return payload['sub']
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                'Invalid scope for token',
            )
        except JWTError:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                'Could not validate credentials',
            )

    async def get_user_by_email(
        self,
        email: str,
        db: AsyncSession = Depends(get_db)
    ) -> Response | None:
        user = await db.execute(select(User).where(User.email == email))

        return user.scalar_one_or_none()

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
    ):
        credentials_exception = HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            'Could not validate credentials',
            {'WWW-Authenticate': 'Bearer'},
        )

        try:
            payload = jwt.decode(
                token,
                self.__SECRET,
                [self.__ALGORITHM],
            )

            if payload['scope'] != 'access_token' or payload['sub'] is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        if not (user := await self.get_user_by_email(payload['sub'], db)):
            raise credentials_exception

        return user


auth_service = Auth()
