from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, User
from src.schemas.user import Request, Response, TokenSchema
from src.services.auth import auth_service


async def create(
    body: Request,
    db: AsyncSession = Depends(get_db)
) -> Response:
    user = User(email=body.username, password=body.password)

    db.add(user)

    await db.commit()
    await db.refresh(user)

    return user


async def update(
    user: User,
    db: AsyncSession,
    revoke: bool = False
) -> TokenSchema | None:
    if revoke:
        user.token = None
    else:
        result = {
            'access_token': await auth_service.create_token(user.email),
            'refresh_token': await auth_service.create_token(user.email, True),
            'token_type': 'bearer',
        }

        user.token = result['refresh_token']

    await db.commit()

    return result or None
