from dotenv import load_dotenv
from os import environ


def environment(variable: str = 'URL') -> str:
    load_dotenv()

    return environ[variable]
