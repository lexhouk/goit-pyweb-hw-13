from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from uvicorn import run

from src.database import get_db
from src.routes.auth import router as auth_router
from src.routes.contacts import router as contacts_router
from src.services.environment import environment


class EmailSchema(BaseModel):
    email: EmailStr


app = FastAPI()

app.include_router(auth_router, prefix='/api')
app.include_router(contacts_router, prefix='/api')


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


@app.post('/send-email')
async def send_email(
    background_tasks: BackgroundTasks,
    body: EmailSchema
) -> dict:
    PREFIX = 'FASTAPIMAIL_'

    conf = ConnectionConfig(
        MAIL_FROM_NAME='Example email',
        TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
        **{
            key[len(PREFIX):]: value
            for key, value in environment().items() if key.startswith(PREFIX)
        },
    )

    background_tasks.add_task(
        FastMail(conf).send_message,
        MessageSchema(
            subject='Fastapi mail module',
            recipients=[body.email],
            template_body={'fullname': 'Billy Jones'},
            subtype=MessageType.html,
        ),
        template_name='example_email.html',
    )

    return {'message': 'email has been sent'}


if __name__ == '__main__':
    run('main:app', host='0.0.0.0', port=8000, reload=True)
