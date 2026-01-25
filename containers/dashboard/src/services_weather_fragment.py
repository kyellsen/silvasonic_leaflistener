class WeatherService:
    @staticmethod
    def get_current_weather():
        """Get the latest weather measurement."""
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT * FROM weather.measurements 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                row = conn.execute(query).fetchone()
                if row:
                    d = dict(row._mapping)
                    if d.get('timestamp') and d['timestamp'].tzinfo is None:
                        d['timestamp'] = d['timestamp'].replace(tzinfo=timezone.utc)
                    return d
        except Exception as e:
            print(f"Weather DB Error: {e}")
        return None

    @staticmethod
    def get_history(hours=24):
        """Get weather history for charts."""
        try:
            with db.get_connection() as conn:
                query = text("""
                    SELECT * FROM weather.measurements 
                    WHERE timestamp >= NOW() - INTERVAL ':hours HOURS'
                    ORDER BY timestamp ASC
                """)
                # Bind param properly or safe f-string for int
                query = text(f"SELECT * FROM weather.measurements WHERE timestamp >= NOW() - INTERVAL '{int(hours)} HOURS' ORDER BY timestamp ASC")
                
                result = conn.execute(query)
                data = {
                    "labels": [],
                    "temp": [],
                    "humidity": [],
                    "rain": [],
                    "wind": []
                }
                
                for row in result:
                    d = dict(row._mapping)
                    ts = d['timestamp']
                    if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                    
                    data["labels"].append(ts.strftime("%H:%M"))
                    data["temp"].append(d.get("temperature_c"))
                    data["humidity"].append(d.get("humidity_percent"))
                    data["rain"].append(d.get("precipitation_mm"))
                    data["wind"].append(d.get("wind_speed_ms"))
                    
                return data
        except Exception as e:
            print(f"Weather History Error: {e}")
            return {"labels": [], "temp": [], "humidity": [], "rain": [], "wind": []}

    @staticmethod
    def get_status():
        """Get service status from JSON file."""
        try:
            status_file = os.path.join(STATUS_DIR, "weather.json")
            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    data = json.load(f)
                    # Check staleness (20 mins schedule, so maybe 25 min stale check)
                    if time.time() - data.get("timestamp", 0) > 1500:
                        data["status"] = "Stalen"
                    return data
        except:
             pass
        return {"status": "Unknown"}
