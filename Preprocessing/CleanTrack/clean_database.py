import os
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

Base = declarative_base()

class CleanPost(Base):
    """SQLAlchemy Model for the processed, clean data."""
    __tablename__ = 'cleaned_posts'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), unique=True, nullable=False)
    
    # Store both so you have a direct comparison for error analysis later
    original_text = Column(Text)
    cleaned_text = Column(Text)
    
    # Classification targets
    label = Column(Integer)             # 1 for AI, 0 for Human
    split_group = Column(String(10))    # 'train', 'val', or 'test'
    
    # Transformer Tokens stored natively as JSON arrays!
    input_ids = Column(JSON)
    attention_mask = Column(JSON)

class CleanDatabaseManager:
    """Manages the connection to the new cleaned_data database."""
    def __init__(self):
        # Route this to the Data/Processed folder
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        db_path = os.path.join(project_root, 'Data', 'Processed', 'cleaned_data.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize SQLAlchemy Engine
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()