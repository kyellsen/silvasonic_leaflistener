import os
from sqlalchemy import text
from datetime import timezone
from .database import db
from .common import logger

class AnalyzerService:
    @staticmethod
    async def get_recent_analysis(limit=20):
        try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        af.filename,
                        af.duration_sec,
                        af.file_size_bytes,
                        af.created_at,
                        am.rms_loudness,
                        am.peak_frequency_hz,
                        art.filepath as spec_path
                    FROM brain.audio_files af
                    LEFT JOIN brain.analysis_metrics am ON af.id = am.audio_file_id
                    LEFT JOIN brain.artifacts art ON af.id = art.audio_file_id AND art.artifact_type = 'spectrogram'
                    ORDER BY af.created_at DESC
                    LIMIT :limit
                """)
                result = await conn.execute(query, {"limit": limit})
                items = []
                for row in result:
                    d = dict(row._mapping)
                    if d.get('created_at'):
                        if d['created_at'].tzinfo is None:
                            d['created_at'] = d['created_at'].replace(tzinfo=timezone.utc)
                        d['created_at_iso'] = d['created_at'].isoformat()
                    else:
                        d['created_at_iso'] = ""
                        
                    # Fix spec path
                    if d.get('spec_path'):
                         fname = os.path.basename(d['spec_path'])
                         d['spec_url'] = f"/api/spectrogram/{fname}"
                    else:
                         d['spec_url'] = None
                         
                    # Format size
                    if d.get('file_size_bytes'):
                        d['size_mb'] = round(d['file_size_bytes'] / (1024*1024), 2)
                    else:
                        d['size_mb'] = 0
                    
                    # Round metrics
                    if d.get('rms_loudness'): d['rms_loudness'] = round(d['rms_loudness'], 1)
                    if d.get('peak_frequency_hz'): d['peak_frequency_hz'] = int(d['peak_frequency_hz'])
                        
                    items.append(d)
                return items
        except Exception as e:
            logger.error(f"Analyzer Error: {e}", exc_info=True)
            return []

    @staticmethod
    async def get_stats():
         try:
            async with db.get_connection() as conn:
                query = text("""
                    SELECT 
                        COUNT(*) as total_files,
                        COALESCE(SUM(duration_sec), 0) as total_duration,
                        AVG(duration_sec) as avg_duration,
                        AVG(file_size_bytes) as avg_size
                    FROM brain.audio_files
                """)
                res = (await conn.execute(query)).fetchone()
                if res:
                    d = dict(res._mapping)
                    d['total_duration_hours'] = round(d['total_duration'] / 3600, 2)
                    d['avg_size_mb'] = round((d['avg_size'] or 0) / (1024*1024), 2)
                    d['avg_duration'] = round(d.get('avg_duration') or 0, 1)
                    return d
                return {}
         except Exception as e:
             logger.error(f"Analyzer Stats Error: {e}", exc_info=True)
             return {}
