from os import environ

from dotenv import load_dotenv


def environment(variable: str = None) -> dict | str:
    load_dotenv()

    return environ[variable] if variable else environ
