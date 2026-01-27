import psycopg2
import os
from datetime import datetime, timezone, timedelta
import random

# Connection params
DB_HOST = "127.0.0.1"
DB_PORT = "5432"
DB_NAME = "silvasonic"
DB_USER = "silvasonic"
DB_PASS = "silvasonic"

def seed():
    print(f"Seeding Database at {DB_HOST}:{DB_PORT}/{DB_NAME}")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        cur = conn.cursor()
        
        # Ensure schema exists (it should)
        cur.execute("CREATE SCHEMA IF NOT EXISTS birdnet")
        
        # Insert Species Info (so joins work)
        species = [
            ("Turdus merula", "Common Blackbird", "Amsel"),
            ("Cyanistes caeruleus", "Eurasian Blue Tit", "Blaumeise"),
            ("Erithacus rubecula", "European Robin", "Rotkehlchen")
        ]
        
        for sci, com, ger in species:
            cur.execute("""
                INSERT INTO birdnet.species_info (scientific_name, common_name, german_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (scientific_name) DO NOTHING
            """, (sci, com, ger))
            
        # Insert Detections
        # Generate some for today and yesterday
        now = datetime.now(timezone.utc)
        
        detections = []
        for i in range(20):
            # Random time in last 48 hours
            dt = now - timedelta(hours=random.randint(0, 48), minutes=random.randint(0, 59))
            sp = random.choice(species)
            
            detections.append({
                "timestamp": dt,
                "filename": f"test_recording_{i}.wav",
                "filepath": f"/data/recording/test_recording_{i}.wav",
                "start_time": 0.0,
                "end_time": 3.0,
                "confidence": 0.8 + (random.random() * 0.15),
                "scientific_name": sp[0],
                "common_name": sp[1],
                "source_device": "test_script"
            })
            
        print(f"Inserting {len(detections)} test detections...")
        
        for d in detections:
            cur.execute("""
                INSERT INTO birdnet.detections 
                (timestamp, filename, filepath, start_time, end_time, confidence, scientific_name, common_name, source_device)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                d["timestamp"], d["filename"], d["filepath"], 
                d["start_time"], d["end_time"], d["confidence"], 
                d["scientific_name"], d["common_name"], d["source_device"]
            ))
            
        conn.commit()
        print("Seeding complete.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Seeding failed: {e}")

if __name__ == "__main__":
    seed()
