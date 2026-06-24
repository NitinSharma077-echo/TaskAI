import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "TaskPilot AI")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./taskpilot.db")


settings = Settings()