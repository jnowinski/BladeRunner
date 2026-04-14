import os
import sqlite3
from contextlib import contextmanager

class RawDatabaseManager:
    """Manages the connection to the new raw_data database."""
    def __init__(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.db_path = os.path.join(project_root, 'Data', 'Processed', 'raw_data.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def create_tables(self):
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS raw_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE NOT NULL,
            split_group TEXT,
            label INTEGER,
            perplexity REAL,
            burstiness REAL,
            punctuation_density REAL,
            lexical_diversity REAL
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()