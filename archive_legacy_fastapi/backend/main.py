import uvicorn

from backend.app import create_app
from backend.config import Settings
from backend.db import Database


settings = Settings.from_env()
database = Database(settings.database)
app = create_app(database=database, settings=settings, serve_static=True)


def main() -> None:
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()