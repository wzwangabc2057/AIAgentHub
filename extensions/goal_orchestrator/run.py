from uvicorn import run
from .app import app
from .config import settings


if __name__ == "__main__":
    run(app, host=settings.host, port=settings.port)
