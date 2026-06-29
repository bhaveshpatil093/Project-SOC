"""
Local SQLite Persistence Layer
==============================
Provides local storage for operational entities (alerts, feedback, features)
since write-back to Elasticsearch is disabled. Uses aiosqlite for non-blocking
async database operations.
"""

import json
from typing import Optional, List

import aiosqlite

from app.logging_config import get_logger
logger = get_logger(__name__)

async def init_db(db_path: str):
    """
    Initializes the SQLite database, creating tables if they do not exist.
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS soc_alerts (
                alert_id TEXT PRIMARY KEY,
                entity_key TEXT, host_id TEXT, user_name TEXT, log_type TEXT,
                threat_score REAL, threat_level TEXT,
                anomaly_scores TEXT,      
                shap_features TEXT,       
                triggered_rules TEXT,     
                mitre_tactic TEXT, mitre_technique TEXT,
                human_explanation TEXT,
                alert_status TEXT DEFAULT 'open',
                suppressed INTEGER DEFAULT 0,
                created_at TEXT,          
                raw_context TEXT          
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS soc_feedback (
                feedback_id TEXT PRIMARY KEY,
                alert_id TEXT, analyst_name TEXT,
                label TEXT,               
                notes TEXT, mitre_override TEXT,
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS soc_features (
                feature_id TEXT PRIMARY KEY,
                entity_key TEXT, host_id TEXT, user_name TEXT,
                window_bucket TEXT,
                feature_vector TEXT,      
                feature_names TEXT,       
                created_at TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS soc_training_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT,            
                status TEXT,              
                summary TEXT,             
                started_at TEXT, finished_at TEXT
            )
        ''')
        
        await db.commit()
        logger.info(f"Database initialized at {db_path}")

async def insert_alert(db_path: str, alert: dict) -> str:
    """Inserts a new alert into the soc_alerts table."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            INSERT INTO soc_alerts (
                alert_id, entity_key, host_id, user_name, log_type,
                threat_score, threat_level, anomaly_scores, shap_features,
                triggered_rules, mitre_tactic, mitre_technique, human_explanation,
                alert_status, suppressed, created_at, raw_context
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.get('alert_id'), alert.get('entity_key'), alert.get('host_id'),
            alert.get('user_name'), alert.get('log_type'), alert.get('threat_score'),
            alert.get('threat_level'), json.dumps(alert.get('anomaly_scores', {})),
            json.dumps(alert.get('shap_features', {})), json.dumps(alert.get('triggered_rules', [])),
            alert.get('mitre_tactic'), alert.get('mitre_technique'), alert.get('human_explanation'),
            alert.get('alert_status', 'open'), alert.get('suppressed', 0),
            alert.get('created_at'), json.dumps(alert.get('raw_context', {}))
        ))
        await db.commit()
        return alert.get('alert_id')

def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

async def list_alerts(db_path: str, status: Optional[str] = None, limit: int = 50, offset: int = 0, host_id: Optional[str] = None) -> List[dict]:
    """Lists alerts from the soc_alerts table with optional filtering."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = _dict_factory
        query = "SELECT * FROM soc_alerts WHERE 1=1"
        params = []
        
        if status:
            query += " AND alert_status = ?"
            params.append(status)
        if host_id:
            query += " AND host_id = ?"
            params.append(host_id)
            
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            
            # Parse JSON fields
            for row in rows:
                for field in ['anomaly_scores', 'shap_features', 'triggered_rules', 'raw_context']:
                    if row.get(field):
                        try:
                            row[field] = json.loads(row[field])
                        except Exception:
                            pass
            return rows

async def get_alert(db_path: str, alert_id: str) -> Optional[dict]:
    """Retrieves a single alert by its ID."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = _dict_factory
        async with db.execute("SELECT * FROM soc_alerts WHERE alert_id = ?", (alert_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                for field in ['anomaly_scores', 'shap_features', 'triggered_rules', 'raw_context']:
                    if row.get(field):
                        try:
                            row[field] = json.loads(row[field])
                        except Exception:
                            pass
            return row

async def update_alert_status(db_path: str, alert_id: str, status: str):
    """Updates the status of an alert."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE soc_alerts SET alert_status = ? WHERE alert_id = ?", (status, alert_id))
        await db.commit()

async def insert_feedback(db_path: str, feedback: dict) -> str:
    """Inserts a new feedback record into the soc_feedback table."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            INSERT INTO soc_feedback (
                feedback_id, alert_id, analyst_name, label, notes, mitre_override, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback.get('feedback_id'), feedback.get('alert_id'), feedback.get('analyst_name'),
            feedback.get('label'), feedback.get('notes'), feedback.get('mitre_override'),
            feedback.get('created_at')
        ))
        await db.commit()
        return feedback.get('feedback_id')

async def list_feedback(db_path: str, label: Optional[str] = None, limit: int = 500) -> List[dict]:
    """Lists feedback records with optional filtering."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = _dict_factory
        query = "SELECT * FROM soc_feedback WHERE 1=1"
        params = []
        
        if label:
            query += " AND label = ?"
            params.append(label)
            
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

async def insert_feature_vector(db_path: str, record: dict):
    """Inserts a feature vector record."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            INSERT INTO soc_features (
                feature_id, entity_key, host_id, user_name, window_bucket,
                feature_vector, feature_names, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('feature_id'), record.get('entity_key'), record.get('host_id'),
            record.get('user_name'), record.get('window_bucket'),
            json.dumps(record.get('feature_vector', [])), json.dumps(record.get('feature_names', [])),
            record.get('created_at')
        ))
        await db.commit()

async def upsert_training_job(db_path: str, job: dict):
    """Inserts or updates a training job record."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            INSERT INTO soc_training_jobs (
                job_id, job_type, status, summary, started_at, finished_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status=excluded.status,
                summary=excluded.summary,
                finished_at=excluded.finished_at
        ''', (
            job.get('job_id'), job.get('job_type'), job.get('status'),
            json.dumps(job.get('summary', {})), job.get('started_at'), job.get('finished_at')
        ))
        await db.commit()

async def get_training_job(db_path: str, job_id: str) -> Optional[dict]:
    """Retrieves a single training job by its ID."""
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = _dict_factory
        async with db.execute("SELECT * FROM soc_training_jobs WHERE job_id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row.get('summary'):
                try:
                    row['summary'] = json.loads(row['summary'])
                except Exception:
                    pass
            return row
