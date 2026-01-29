import os

from sqlalchemy import create_engine, text


def fix_db():
    # Use environment variables or defaults matching docker-compose
    user = os.getenv("POSTGRES_USER", "silvasonic")
    password = os.getenv("POSTGRES_PASSWORD", "silvasonic")
    db_name = os.getenv("POSTGRES_DB", "silvasonic")
    host = os.getenv(
        "POSTGRES_HOST", "localhost"
    )  # Use localhost for running from host with port 5432
    port = os.getenv("POSTGRES_PORT", "5432")

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    print(f"Connecting to {db_url}...")

    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(
                text("COMMIT")
            )  # Ensure we are not in a transaction block for some DDL if needed? implicit commit usually

            # 1. Add uploaded_at to recordings
            print("Checking recordings table...")
            try:
                conn.execute(
                    text("ALTER TABLE recordings ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMPTZ")
                )
                conn.execute(text("COMMIT"))
                print("Added uploaded_at column.")
            except Exception as e:
                print(f"Error adding uploaded_at: {e}")

            # 2. Create uploads table
            print("Creating uploads table...")
            create_uploads_sql = """
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                remote_path TEXT,
                size_bytes BIGINT,
                status TEXT NOT NULL, -- 'success', 'failed'
                error_message TEXT,
                upload_time TIMESTAMPTZ DEFAULT NOW()
            );
            """
            conn.execute(text(create_uploads_sql))
            conn.execute(text("COMMIT"))
            print("Created uploads table.")

            # 3. Create hypertable if timescaledb is used (optional but consistent)
            # Check if hypertable exists or create it.
            # Ignore failure if it's already a hypertable or timescaledb not active
            try:
                conn.execute(
                    text(
                        "SELECT create_hypertable('uploads', 'upload_time', if_not_exists => TRUE);"
                    )
                )
                conn.execute(text("COMMIT"))
                print("Converted uploads to hypertable.")
            except Exception as e:
                print(f"Hypertable creation info (might be normal if standard postgres): {e}")

    except Exception as e:
        print(f"Database connection failed: {e}")


if __name__ == "__main__":
    fix_db()
