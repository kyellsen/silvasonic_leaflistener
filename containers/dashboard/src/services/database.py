import os
from sqlalchemy.ext.asyncio import create_async_engine

class DatabaseHandler:
    def __init__(self):
        self.user = os.getenv("POSTGRES_USER", "silvasonic")
        self.password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
        self.db_name = os.getenv("POSTGRES_DB", "silvasonic")
        self.host = os.getenv("POSTGRES_HOST", "db")
        self.port = os.getenv("POSTGRES_PORT", "5432")
        
        self.db_url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
        self.engine = create_async_engine(self.db_url, pool_pre_ping=True)
        # self.Session = sessionmaker(bind=self.engine) # We primarily use direct connection in this legacy code

    def get_connection(self):
        return self.engine.connect()

db = DatabaseHandler()
