"""
Database models and connection manager using SQLAlchemy.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, 
    DateTime, ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool

from Scraper.config import DATABASE_CONFIG

Base = declarative_base()


class Post(Base):
    """Model for social media posts."""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    platform_url = Column(Text)
    
    # Content
    text = Column(Text)
    language = Column(String(10))
    
    # Author information
    author_id = Column(String(255))
    author_username = Column(String(255))
    author_display_name = Column(String(255))
    author_followers = Column(Integer)
    
    # Engagement metrics
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    retweet_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    # Post properties
    is_reply = Column(Boolean, default=False)
    is_repost = Column(Boolean, default=False)
    has_media = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Classification fields
    sentiment = Column(String(20))
    category = Column(String(100))
    
    # Raw platform-specific data
    raw_json = Column(JSON)
    
    # Relationships
    hashtags = relationship('PostHashtag', back_populates='post', cascade='all, delete-orphan')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('post_id', 'platform', name='unique_post_per_platform'),
        Index('idx_posts_platform_created', 'platform', 'created_at'),
        Index('idx_posts_author', 'author_username'),
        Index('idx_posts_scraped_at', 'scraped_at'),
    )
    
    def __repr__(self):
        return f'<Post {self.platform}:{self.post_id}>'


class PostHashtag(Base):
    """Model for post hashtags (many-to-many)."""
    __tablename__ = 'post_hashtags'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    hashtag = Column(String(255), nullable=False)
    
    # Relationships
    post = relationship('Post', back_populates='hashtags')
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('post_id', 'hashtag', name='unique_post_hashtag'),
        Index('idx_hashtags_hashtag', 'hashtag'),
        Index('idx_hashtags_post_id', 'post_id'),
    )
    
    def __repr__(self):
        return f'<PostHashtag #{self.hashtag}>'


class ScraperState(Base):
    """Model for tracking scraper state."""
    __tablename__ = 'scraper_state'
    
    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)
    query = Column(String(500))
    last_post_id = Column(String(255))
    last_timestamp = Column(DateTime(timezone=True))
    cursor = Column(Text)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('platform', 'query', name='unique_platform_query'),
        Index('idx_scraper_state_platform', 'platform'),
    )
    
    def __repr__(self):
        return f'<ScraperState {self.platform}:{self.query}>'


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        """Initialize database connection."""
        # Ensure data directory exists
        import os
        db_path = DATABASE_CONFIG['db_path']
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # SQLite connection string
        db_url = f"sqlite:///{db_path}"
        
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            connect_args={'check_same_thread': False},  # Allow multi-threading
        )
        
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """
        Context manager for database sessions.
        
        Usage:
            with db_manager.get_session() as session:
                session.query(Post).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def insert_post(self, post_data: Dict[str, Any], hashtags: List[str] = None) -> Optional[int]:
        """
        Insert a single post into the database.
        
        Args:
            post_data: Dictionary containing post fields
            hashtags: List of hashtag strings
        
        Returns:
            Post ID if successful, None otherwise
        """
        with self.get_session() as session:
            try:
                # Create post object
                post = Post(**post_data)
                session.add(post)
                session.flush()  # Get the post ID
                
                # Add hashtags if provided
                if hashtags:
                    for tag in hashtags:
                        hashtag = PostHashtag(post_id=post.id, hashtag=tag.lower())
                        session.add(hashtag)
                
                session.commit()
                return post.id
            except Exception as e:
                # Handle duplicate post (unique constraint violation)
                if 'unique_post_per_platform' in str(e):
                    return None
                raise
    
    def bulk_insert(self, posts_data: List[Dict[str, Any]]) -> int:
        """
        Insert multiple posts at once.
        
        Args:
            posts_data: List of dictionaries containing post data and hashtags
        
        Returns:
            Number of posts successfully inserted
        """
        inserted_count = 0
        skipped_duplicates = 0
        
        with self.get_session() as session:
            for post_item in posts_data:
                try:
                    # Separate hashtags from post data (make a copy to avoid modifying original)
                    post_data = post_item.copy()
                    hashtags = post_data.pop('hashtags', [])
                    
                    # Check if post already exists to avoid IntegrityError
                    existing = session.query(Post).filter_by(
                        post_id=post_data.get('post_id'),
                        platform=post_data.get('platform')
                    ).first()
                    
                    if existing:
                        # Skip duplicate
                        skipped_duplicates += 1
                        continue
                    
                    # Create new post
                    post = Post(**post_data)
                    session.add(post)
                    session.flush()
                    
                    # Add hashtags
                    for tag in hashtags:
                        hashtag = PostHashtag(post_id=post.id, hashtag=tag.lower())
                        session.add(hashtag)
                    
                    inserted_count += 1
                    
                except Exception as e:
                    # Log unexpected errors (shouldn't happen with duplicate check above)
                    error_str = str(e).lower()
                    if 'unique constraint' not in error_str and 'duplicate' not in error_str:
                        logging.error(f"Error inserting post {post_data.get('post_id')}: {e}")
                    continue
            
            # Commit all successful inserts at once
            try:
                session.commit()
            except Exception as e:
                logging.error(f"Error committing posts: {e}")
                session.rollback()
                return 0
        
        if skipped_duplicates > 0:
            logging.debug(f"Skipped {skipped_duplicates} duplicate posts")
        
        return inserted_count
    
    def upsert_post(self, post_data: Dict[str, Any], hashtags: List[str] = None) -> int:
        """
        Insert or update a post.
        
        Args:
            post_data: Dictionary containing post fields
            hashtags: List of hashtag strings
        
        Returns:
            Post ID
        """
        with self.get_session() as session:
            # Check if post exists
            existing = session.query(Post).filter_by(
                post_id=post_data['post_id'],
                platform=post_data['platform']
            ).first()
            
            if existing:
                # Update existing post
                for key, value in post_data.items():
                    setattr(existing, key, value)
                post_id = existing.id
            else:
                # Insert new post
                post = Post(**post_data)
                session.add(post)
                session.flush()
                post_id = post.id
                
                # Add hashtags
                if hashtags:
                    for tag in hashtags:
                        hashtag = PostHashtag(post_id=post_id, hashtag=tag.lower())
                        session.add(hashtag)
            
            session.commit()
            return post_id
    
    def get_scraper_state(self, platform: str, query: str = None) -> Optional[ScraperState]:
        """Get the last scraper state for a platform/query."""
        with self.get_session() as session:
            state = session.query(ScraperState).filter_by(
                platform=platform,
                query=query
            ).first()
            if state:
                # Expunge to detach from session so it can be used outside the context
                session.expunge(state)
            return state
    
    def update_scraper_state(self, platform: str, query: str = None, 
                           last_post_id: str = None, last_timestamp: datetime = None,
                           cursor: str = None):
        """Update scraper state for incremental scraping."""
        with self.get_session() as session:
            state = session.query(ScraperState).filter_by(
                platform=platform,
                query=query
            ).first()
            
            if state:
                # Update existing state
                if last_post_id:
                    state.last_post_id = last_post_id
                if last_timestamp:
                    state.last_timestamp = last_timestamp
                if cursor:
                    state.cursor = cursor
                state.updated_at = datetime.utcnow()
            else:
                # Create new state
                state = ScraperState(
                    platform=platform,
                    query=query,
                    last_post_id=last_post_id,
                    last_timestamp=last_timestamp,
                    cursor=cursor
                )
                session.add(state)
            
            session.commit()
    
    def get_post_count(self, platform: str = None) -> int:
        """Get total post count, optionally filtered by platform."""
        with self.get_session() as session:
            query = session.query(Post)
            if platform:
                query = query.filter_by(platform=platform)
            return query.count()
    
    def get_recent_posts(self, platform: str = None, limit: int = 10) -> List[Post]:
        """Get most recent posts."""
        with self.get_session() as session:
            query = session.query(Post)
            if platform:
                query = query.filter_by(platform=platform)
            return query.order_by(Post.scraped_at.desc()).limit(limit).all()
