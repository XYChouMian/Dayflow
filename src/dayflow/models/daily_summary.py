"""Daily summary model - stores AI-generated daily summaries and user notes."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from dayflow.models.database import Base


class DailySummary(Base):
    """Model for storing daily summaries with AI analysis and user notes."""

    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    ai_summary = Column(Text, nullable=True)  # AI-generated summary
    user_notes = Column(Text, nullable=True)  # User's personal notes
    total_minutes = Column(Integer, nullable=True)  # Total tracked time
    productive_minutes = Column(Integer, nullable=True)  # Productive time
    activity_count = Column(Integer, nullable=True)  # Number of activities
    top_category = Column(String, nullable=True)  # Most time-spent category
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<DailySummary(id={self.id}, "
            f"date={self.date}, "
            f"activity_count={self.activity_count})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "ai_summary": self.ai_summary,
            "user_notes": self.user_notes,
            "total_minutes": self.total_minutes,
            "productive_minutes": self.productive_minutes,
            "activity_count": self.activity_count,
            "top_category": self.top_category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
