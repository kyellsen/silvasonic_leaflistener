import logging
import traceback
import json
from datetime import datetime
from sqlalchemy.orm import Session
from src.core.database import SessionLocal, AudioFile, AnalysisMetrics, Artifact, init_db
from src.config import config
from src.analyzers.meta import MetaAnalyzer
from src.analyzers.loudness import LoudnessAnalyzer
from src.analyzers.frequency import FrequencyAnalyzer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Pipeline")

class AnalysisPipeline:
    def __init__(self):
        self.analyzers = [
            MetaAnalyzer(),
            LoudnessAnalyzer(),
            FrequencyAnalyzer()
        ]
        
    def process_file(self, filepath: str):
        logger.info(f"Starting processing for: {filepath}")
        db: Session = SessionLocal()
        
        try:
            # 1. Check if exists
            existing = db.query(AudioFile).filter_by(filepath=filepath).first()
            if existing and existing.processed_at:
                logger.info(f"Skipping {filepath}, already processed.")
                return

            # 2. Create AudioFile record
            audio_file = existing or AudioFile(
                filepath=filepath,
                filename=filepath.split('/')[-1]
            )
            if not existing:
                db.add(audio_file)
                db.commit() # Get ID
            
            # 3. Run Analyzers
            results = {}
            for analyzer in self.analyzers:
                try:
                    logger.info(f"Running {analyzer.name}...")
                    res = analyzer.analyze(filepath)
                    results.update(res)
                except Exception as e:
                    logger.error(f"Analyzer {analyzer.name} failed: {e}")
                    traceback.print_exc()
            
            # 4. Save Results
            # Update AudioFile Meta
            audio_file.duration_sec = results.get("duration_sec")
            audio_file.sample_rate = results.get("sample_rate")
            audio_file.channels = results.get("channels")
            audio_file.file_size_bytes = results.get("file_size_bytes")
            
            # Save Metrics
            metrics = AnalysisMetrics(
                audio_file_id=audio_file.id,
                rms_loudness=results.get("rms_loudness"),
                peak_frequency_hz=results.get("peak_frequency_hz"),
                is_active=results.get("is_active", False)
            )
            db.add(metrics)
            
            # Save Artifacts
            if "spectrogram_path" in results:
                spec = Artifact(
                    audio_file_id=audio_file.id,
                    artifact_type="spectrogram",
                    filepath=results["spectrogram_path"]
                )
                db.add(spec)
                
            audio_file.processed_at = datetime.utcnow()
            db.commit()

            # 5. Export JSON Metadata (Opt-Out)
            if config.EXPORT_JSON_METADATA:
                try:
                    json_path = config.METADATA_DIR / f"{audio_file.filename}.json"
                    
                    # Construct JSON payload
                    payload = {
                        "filename": audio_file.filename,
                        "processed_at": audio_file.processed_at.isoformat(),
                        "meta": {
                            "duration_sec": audio_file.duration_sec,
                            "sample_rate": audio_file.sample_rate,
                            "channels": audio_file.channels,
                            "file_size_bytes": audio_file.file_size_bytes
                        },
                        "metrics": {
                            "rms_loudness": metrics.rms_loudness,
                            "peak_frequency_hz": metrics.peak_frequency_hz,
                            "is_active": metrics.is_active
                        },
                        "artifacts": results.get("spectrogram_path")
                    }
                    
                    with open(json_path, "w") as f:
                        json.dump(payload, f, indent=2)
                        
                    logger.info(f"Exported JSON metadata to {json_path}")
                except Exception as e:
                    logger.error(f"Failed to export JSON metadata: {e}")
                    # Non-blocking error, we don't rollback DB

            logger.info(f"Successfully processed {filepath}")

        except Exception as e:
            logger.error(f"Pipeline failed for {filepath}: {e}")
            db.rollback()
        finally:
            db.close()
