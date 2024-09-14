from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, \
    Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, \
    OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repository.users import create, update, verify
from src.services.auth import auth_service, Token
from src.services.email import send
from src.schemas.user import TokenSchema, UserRequest


router = APIRouter(prefix='/auth', tags=['Authorization'])

get_refresh_token = HTTPBearer()


@router.post('/signup', status_code=status.HTTP_201_CREATED)
async def signup(
    body: UserRequest,
    background: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> dict:
    if await auth_service.get_user_by_email(body.username, db):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Account already exists',
        )

    body.password = auth_service.get_password_hash(body.password)

    user = await create(body, db)

    background.add_task(send, user.email, request.base_url)

    message = 'User successfully created. Check your email for confirmation.'

    return {'detail': message}


@router.post('/login')
async def login(
    body: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> TokenSchema:
    if not (user := await auth_service.get_user_by_email(body.username, db)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid email')

    if not user.verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Email not verified')

    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid password')

    return await update(user, db)


@router.get('/refresh-token')
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(get_refresh_token),
    db: AsyncSession = Depends(get_db)
) -> TokenSchema:
    token = credentials.credentials

    email = await auth_service.decode_token(token, Token.REFRESH)

    user = await auth_service.get_user_by_email(email, db)

    if user.token != token:
        await update(user, db, True)

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            'Invalid refresh token',
        )

    return await update(user, db)


@router.get('/verify/{token}', status_code=status.HTTP_202_ACCEPTED)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    email = await auth_service.decode_token(token)

    if not (user := await auth_service.get_user_by_email(email, db)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Verification error')

    if user.verified:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Your email is already verified',
        )

    await verify(email, db)

    return {'message': 'Email verified'}
