from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from .auth import auth_service
from .environment import environment


async def send(address: EmailStr, host: str) -> None:
    TOKEN = await auth_service.create_token(address, expire=True)
    PREFIX = 'FASTAPIMAIL_'

    config = ConnectionConfig(
        MAIL_FROM_NAME='Contacts API',
        TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
        **{
            key[len(PREFIX):]: value
            for key, value in environment().items() if key.startswith(PREFIX)
        },
    )

    try:
        message = MessageSchema(
            subject='Confirm your email',
            recipients=[address],
            template_body={'url': f'{host}api/auth/verify/{TOKEN}'},
            subtype=MessageType.html,
        )

        await FastMail(config).send_message(message, 'email.html')
    except ConnectionErrors as err:
        print(err)
