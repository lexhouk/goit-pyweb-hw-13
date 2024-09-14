from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, \
    OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repository.users import create, update
from src.services.auth import auth_service
from src.schemas.user import Request, TokenSchema, Response


router = APIRouter(prefix='/auth', tags=['Authorization'])

get_refresh_token = HTTPBearer()


@router.post('/signup', status_code=status.HTTP_201_CREATED)
async def signup(
    body: Request,
    db: AsyncSession = Depends(get_db)
) -> Response:
    if await auth_service.get_user_by_email(body.username, db):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Account already exists',
        )

    body.password = auth_service.get_password_hash(body.password)

    return await create(body, db)


@router.post('/login')
async def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> TokenSchema:
    if not (user := await auth_service.get_user_by_email(body.username, db)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid email')

    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid password')

    return await update(user, db)


@router.get('/refresh-token')
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(get_refresh_token),
    db: AsyncSession = Depends(get_db)
) -> TokenSchema:
    token = credentials.credentials

    email = await auth_service.decode_refresh_token(token)

    user = await auth_service.get_user_by_email(email, db)

    if user.token != token:
        await update(user, db, True)

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            'Invalid refresh token',
        )

    return await update(user, db)
