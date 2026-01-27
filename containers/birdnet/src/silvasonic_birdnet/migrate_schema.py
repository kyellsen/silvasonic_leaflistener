import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

def migrate():
    user = os.getenv("POSTGRES_USER", "silvasonic")
    password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
    db_name = os.getenv("POSTGRES_DB", "silvasonic")
    host = os.getenv("POSTGRES_HOST", "db") # Default internal
    port = os.getenv("POSTGRES_PORT", "5432")

    # If running from host causing issues, try localhost if host is 'db'
    if os.environ.get("MIGRATE_FROM_HOST"):
        host = "127.0.0.1"

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    logger.info(f"Connecting to {host}...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("COMMIT")) # Ensure no transaction block
            
            # Check if column exists
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema='birdnet' 
                  AND table_name='detections' 
                  AND column_name='source_device';
            """)
            result = conn.execute(check_sql)
            if result.fetchone():
                logger.info("Column 'source_device' already exists. Skipping.")
            else:
                logger.info("Adding 'source_device' column...")
                alter_sql = text('ALTER TABLE birdnet.detections ADD COLUMN source_device VARCHAR(50) DEFAULT NULL;')
                conn.execute(alter_sql)
                conn.commit()
                logger.info("Migration successful.")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate()
