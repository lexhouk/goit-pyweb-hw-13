from fastapi import Depends, FastAPI, HTTPException, status
from fastapi_limiter import FastAPILimiter
from redis.asyncio import Redis as InitRedis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from uvicorn import run

from src.database import get_db
from src.routes.auth import router as auth_router
from src.routes.contacts import router as contacts_router
from src.services.environment import environment


app = FastAPI()

app.include_router(auth_router, prefix='/api')
app.include_router(contacts_router, prefix='/api')


@app.on_event('startup')
async def startup():
    r = await InitRedis(
        **environment('REDIS', True, True),
        db=0,
        encoding='utf-8',
        decode_responses=True,
    )

    await FastAPILimiter.init(r)


@app.get('/api/healthchecker', tags=['Status'])
async def root(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        if not await db.execute(text('SELECT 1')):
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                'Database is not configured correctly',
            )

        return {'message': 'Welcome to FastAPI!'}
    except Exception as err:
        print(err)

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            'Error connecting to the database',
        )


if __name__ == '__main__':
    run('main:app', host='0.0.0.0', port=8000, reload=True)
