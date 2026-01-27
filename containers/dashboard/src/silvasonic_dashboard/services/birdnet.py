import asyncio
import datetime
import os
import typing

from sqlalchemy import text
from silvasonic_dashboard.settings import SettingsService

from .common import REC_DIR, logger
from .database import db


class BirdNetService:
    @staticmethod
    async def get_recent_detections(limit: int = 10) -> list[dict[str, typing.Any]]:
        try:
            async with db.get_connection() as conn:
                # Query matches BirdNET schema: birdnet.detections table
                # We need to manually split timestamp into date/time map for value compatibility with template
                query = text("""
                    SELECT 
                        d.filepath, 
                        d.start_time, 
                        d.end_time, 
                        d.confidence, 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name, 
                        d.timestamp,
                        d.filename,
                        d.clip_path,
                        s.german_name,
                        s.image_url,
                        s.description
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info s ON d.scientific_name = s.scientific_name
                    ORDER BY d.timestamp DESC 
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})

                detections = []
                use_german = SettingsService.is_german_names_enabled()

                for row in result:
                    d = dict(row._mapping)  # SQLAlchemy Row to dict
                    ts = d.get("timestamp")
                    if ts:
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=datetime.UTC)
                        d["iso_timestamp"] = ts.isoformat()
                        # Legacy support or direct use? We'll use ISO in frontend.
                        d["time"] = (
                            ts.isoformat()
                        )  # Temporary overload for template compatibility check
                    else:
                        d["iso_timestamp"] = ""
                        d["time"] = "-"

                    # Display Name Logic
                    d["display_name"] = (
                        d.get("german_name")
                        if use_german and d.get("german_name")
                        else d.get("com_name")
                    )

                    # Audio Path Logic
                    fp = d.get("filepath")
                    if fp and fp.startswith(REC_DIR):
                        d["audio_relative_path"] = fp[len(REC_DIR) :].lstrip("/")
                    else:
                        d["audio_relative_path"] = d.get("filename")

                    # Playback URL Logic (Clip vs Full)
                    if d.get("clip_path"):
                        d["playback_url"] = f"/api/clips/{os.path.basename(d['clip_path'])}"
                    else:
                        d["playback_url"] = f"/api/audio/{d.get('audio_relative_path')}"

                    # Image Logic (Fallback & Enrichment Trigger)
                    if not d.get("image_url"):
                        d["image_url"] = None
                        # We should try to enrich this species so next time it has an image
                        if d.get("sci_name"):
                            # Fire and forget / Background task?
                            # Or just await it? For "Recent Detections" on dashboard, speed matters.
                            # But if we don't await, we won't show it THIS time.
                            # Let's await for the first few (limit is small, 5).
                            # Check if we already have it in a local cache to avoid DB hits?
                            # limit is small, so we can afford to check.
                            pass  # We will collect distinct species to enrich below

                    detections.append(d)

                # Enrichment Step
                # Collect unique scientific names that are missing images
                missing_images = {}
                for d in detections:
                    if not d.get("image_url") and d.get("sci_name"):
                        missing_images[d["sci_name"]] = d

                if missing_images:
                    # Enrich unique species found
                    for sci_name in missing_images:
                        # Create a dummy dict to pass to enricher (it expects dict with sci_name)
                        info = {
                            "sci_name": sci_name,
                            "com_name": missing_images[sci_name].get("com_name"),
                        }
                        updated_info = await BirdNetService.enrich_species_data(info)

                        # Update all detections with this sci_name
                        if updated_info.get("image_url"):
                            for d in detections:
                                if d.get("sci_name") == sci_name:
                                    d["image_url"] = updated_info.get("image_url")
                                    d["description"] = updated_info.get("description")
                                    # Update German name if we found one
                                    if updated_info.get("german_name"):
                                        d["german_name"] = updated_info.get("german_name")
                                        # Re-evaluate display name
                                        if use_german:
                                            d["display_name"] = d["german_name"]

                return detections
        except Exception as e:
            logger.error(f"DB Error (get_recent_detections): {e}", exc_info=True)
            return []

    @staticmethod
    async def get_detection(filename: str) -> dict[str, typing.Any] | None:
        try:
            async with db.get_connection() as conn:
                # Reconstruct absolute path from relative path input
                # The input 'filename' might be "date_folder/file.wav"
                target_filepath = os.path.join(REC_DIR, filename)

                query = text("""
                    SELECT 
                        d.filepath, 
                        d.start_time, 
                        d.end_time, 
                        d.confidence, 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name, 
                        d.timestamp,
                        d.filename,
                        d.clip_path,
                        s.image_url,
                        s.description,
                        s.german_name,
                        s.wikipedia_url
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info s ON d.scientific_name = s.scientific_name
                    WHERE d.filepath = :filepath OR d.filename = :filename
                """)
                row = (
                    await conn.execute(query, {"filepath": target_filepath, "filename": filename})
                ).fetchone()

                if not row:
                    return None

                d = dict(row._mapping)
                if d.get("timestamp"):
                    if d["timestamp"].tzinfo is None:
                        d["timestamp"] = d["timestamp"].replace(tzinfo=datetime.UTC)
                    d["iso_timestamp"] = d["timestamp"].isoformat()
                    d["formatted_time"] = d["timestamp"].strftime("%d.%m.%Y %H:%M:%S")
                else:
                    d["iso_timestamp"] = ""
                    d["formatted_time"] = "-"

                d["confidence_percent"] = round(d["confidence"] * 100)

                # Display Name Logic
                use_german = SettingsService.is_german_names_enabled()
                d["display_name"] = (
                    d.get("german_name")
                    if use_german and d.get("german_name")
                    else d.get("com_name")
                )

                # Audio Path Logic
                fp = d.get("filepath")
                if fp and fp.startswith(REC_DIR):
                    d["audio_relative_path"] = fp[len(REC_DIR) :].lstrip("/")
                else:
                    d["audio_relative_path"] = d.get("filename")

                # Playback URL
                if d.get("clip_path"):
                    d["playback_url"] = f"/api/clips/{os.path.basename(d['clip_path'])}"
                else:
                    d["playback_url"] = f"/api/audio/{d.get('audio_relative_path')}"

                return d
        except Exception as e:
            logger.error(f"DB Error (get_detection): {e}", exc_info=True)
            return None

    @staticmethod
    async def get_processing_rate(minutes: int = 60) -> float:
        """Calculate files processed per minute over the last X minutes."""
        try:
            async with db.get_connection() as conn:
                # Count from processed_files table
                query = text("""
                    SELECT COUNT(*) 
                    FROM birdnet.processed_files 
                    WHERE processed_at >= NOW() - INTERVAL ':min MINUTES'
                """)
                # Parameter binding for interval string is tricky in some drivers,
                # safer to construct interval in python or use parameter.

                # Postgres logic:
                query = text(
                    "SELECT COUNT(*) FROM birdnet.processed_files WHERE processed_at >= NOW() - make_interval(mins => :mins)"
                )

                count = (await conn.execute(query, {"mins": minutes})).scalar() or 0
                return round(count / minutes, 2)
        except Exception as e:
            # Table might not exist yet if migration failed or legacy system
            # Fallback to detections count? No, that's misleading.
            logger.warning(f"BirdNET Rate Error (probably missing table): {e}")
            return 0.0

    @staticmethod
    @staticmethod
    async def get_latest_processed_filename() -> str | None:
        """Get the filename of the most recently processed file."""
        try:
            async with db.get_connection() as conn:
                # We want the file with the largest filename (latest timestamp), not necessarily processed_at
                # But processed_at sort is safer if processing out of order.
                # However, lag is defined by file order.
                # So MAX(filename) is best cursor.
                query = text("SELECT MAX(filename) FROM birdnet.processed_files")
                return (await conn.execute(query)).scalar()
        except Exception:
            return None

    @staticmethod
    @staticmethod
    async def get_all_species() -> list[dict[str, typing.Any]]:
        """Returns all species with their counts and last seen date. Enriches with images if missing."""
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        d.common_name as com_name, 
                        d.scientific_name as sci_name,
                        COUNT(*) as count,
                        MAX(d.timestamp) as last_seen,
                        MIN(d.timestamp) as first_seen,
                        AVG(d.confidence) as avg_conf,
                        si.image_url,
                        si.german_name
                    FROM birdnet.detections d
                    LEFT JOIN birdnet.species_info si ON d.scientific_name = si.scientific_name
                    GROUP BY d.common_name, d.scientific_name, si.image_url, si.german_name
                    ORDER BY count DESC
                """)
                result = await conn.execute(query)
                species = []

                # List of species that need enrichment
                to_enrich = []

                for row in result:
                    d = dict(row._mapping)
                    # Format dates
                    if d.get("last_seen"):
                        if d["last_seen"].tzinfo is None:
                            d["last_seen"] = d["last_seen"].replace(tzinfo=datetime.UTC)
                        d["last_seen_iso"] = d["last_seen"].isoformat()
                    else:
                        d["last_seen_iso"] = ""

                    if d.get("first_seen"):
                        if d["first_seen"].tzinfo is None:
                            d["first_seen"] = d["first_seen"].replace(tzinfo=datetime.UTC)
                        d["first_seen_iso"] = d["first_seen"].isoformat()
                    else:
                        d["first_seen_iso"] = ""

                    if d.get("avg_conf"):
                        d["avg_conf"] = float(d["avg_conf"])
                    else:
                        d["avg_conf"] = 0.0

                    species.append(d)

                    # Check if enrichment is needed (no image)
                    if not d.get("image_url"):
                        to_enrich.append(d)

                # Enrich in background (parallel)
                if to_enrich:
                    # We limit concurrency to avoid hitting API limits if many are missing
                    # But for now, simple gather is a start.
                    await asyncio.gather(
                        *[BirdNetService.enrich_species_data(sp) for sp in to_enrich]
                    )

                # Display Name Logic (Post-process after enrichment)
                use_german = SettingsService.is_german_names_enabled()
                for sp in species:
                    sp["display_name"] = (
                        sp.get("german_name")
                        if use_german and sp.get("german_name")
                        else sp.get("com_name")
                    )

                return species
        except Exception as e:
            logger.error(f"Error get_all_species: {e}", exc_info=True)
            return []

    @staticmethod
    async def enrich_species_data(info: dict[str, typing.Any]) -> dict[str, typing.Any]:
        """Enrich species info with Wikimedia data, using cache."""
        if not info or not info.get("sci_name"):
            return info

        sci_name = info["sci_name"]

        try:
            async with db.get_connection() as conn:
                # 1. Check Cache
                query_cache = text(
                    "SELECT * FROM birdnet.species_info WHERE scientific_name = :sci_name"
                )
                cache = (await conn.execute(query_cache, {"sci_name": sci_name})).fetchone()

                wiki_data = None
                if cache:
                    wiki_data = dict(cache._mapping)
                    # Check age (optional, e.g. update every 30 days)

                # 2. Fetch if missing
                if not wiki_data:
                    from silvasonic_dashboard.wikimedia import WikimediaService

                    print(f"Fetching Wikimedia data for {sci_name}...")
                    wiki_data = await WikimediaService.fetch_species_data(sci_name)

                    if wiki_data:
                        # 3. Cache Result
                        # We use UPSERT (INSERT ... ON CONFLICT)
                        query_upsert = text("""
                            INSERT INTO birdnet.species_info (
                                scientific_name, common_name, german_name, family, 
                                image_url, description, wikipedia_url, last_updated
                            ) VALUES (
                                :scientific_name, :common_name, :german_name, :family,
                                :image_url, :description, :wikipedia_url, NOW()
                            )
                            ON CONFLICT (scientific_name) DO UPDATE SET
                                german_name = EXCLUDED.german_name,
                                image_url = EXCLUDED.image_url,
                                description = EXCLUDED.description,
                                wikipedia_url = EXCLUDED.wikipedia_url,
                                last_updated = NOW()
                        """)
                        # Fill gaps
                        wiki_data["common_name"] = info.get("com_name")
                        wiki_data["family"] = ""  # ToDo

                        await conn.execute(query_upsert, wiki_data)
                        await conn.commit()

                # 4. Merge
                if wiki_data:
                    info["german_name"] = wiki_data.get("german_name")
                    info["image_url"] = wiki_data.get("image_url")
                    info["description"] = wiki_data.get("description")
                    info["wikipedia_url"] = wiki_data.get("wikipedia_url")

        except Exception as e:
            logger.error(f"Enrichment error for {sci_name}: {e}", exc_info=True)

        return info

    @staticmethod
    async def toggle_watchlist(sci_name: str, com_name: str, enabled: bool) -> bool:
        """Toggle watchlist status for a species."""
        try:
            async with db.get_connection() as conn:
                # Upsert logic (Postgres specific) or check/update
                # Check if exists
                check = text("SELECT id FROM birdnet.watchlist WHERE scientific_name = :sci")
                res = (await conn.execute(check, {"sci": sci_name})).fetchone()

                if res:
                    # Update
                    upd = text(
                        "UPDATE birdnet.watchlist SET enabled = :en, common_name = :com WHERE scientific_name = :sci"
                    )
                    await conn.execute(
                        upd, {"en": 1 if enabled else 0, "com": com_name, "sci": sci_name}
                    )
                else:
                    # Insert
                    ins = text(
                        "INSERT INTO birdnet.watchlist (scientific_name, common_name, enabled) VALUES (:sci, :com, :en)"
                    )
                    await conn.execute(
                        ins, {"sci": sci_name, "com": com_name, "en": 1 if enabled else 0}
                    )

                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Watchlist toggle error: {e}", exc_info=True)
            return False

    @staticmethod
    async def get_watchlist_status(sci_names: list[str]) -> dict[str, bool]:
        """Get watchlist status for a list of scientific names. Returns dict {sci_name: bool}"""
        try:
            if not sci_names:
                return {}
            async with db.get_connection() as conn:
                # For safety/simplicity let's fetch all enabled (watchlist is usually small).

                query_all = text("SELECT scientific_name FROM birdnet.watchlist WHERE enabled = 1")
                res = await conn.execute(query_all)
                watched = {row.scientific_name for row in res}

                return {name: (name in watched) for name in sci_names}
        except Exception as e:
            logger.error(f"Watchlist status error: {e}", exc_info=True)
            return {}
