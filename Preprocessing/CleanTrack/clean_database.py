import os
import sqlite3
from contextlib import contextmanager

class CleanDatabaseManager:
    """Manages the connection to the new cleaned_data database using native SQLite."""
    def __init__(self):
        # Route this to the Data/Processed folder
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.db_path = os.path.join(project_root, 'Data', 'Processed', 'cleaned_data.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def create_tables(self):
        """Creates the cleaned_posts table using a raw SQL command."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS cleaned_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE NOT NULL,
            original_text TEXT,
            cleaned_text TEXT,
            label INTEGER,
            split_group TEXT,
            input_ids TEXT,
            attention_mask TEXT,
            embeddings TEXT   -- NEW: Stored as JSON strings
        );
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            
    @contextmanager
    def get_connection(self):
        """Context manager for SQLite database connection."""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()