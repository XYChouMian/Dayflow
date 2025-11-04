"""Timeline activity model - represents AI-analyzed activity segments."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from dayflow.models.database import Base


class TimelineActivity(Base):
    """Model for storing analyzed timeline activities."""

    __tablename__ = "timeline_activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("timeline_categories.id"), nullable=True)
    timelapse_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to category
    category = relationship("TimelineCategory", back_populates="activities")

    def __repr__(self) -> str:
        return (
            f"<TimelineActivity(id={self.id}, "
            f"title='{self.title}', "
            f"start={self.start_time}, end={self.end_time})>"
        )

    @property
    def duration_minutes(self) -> float:
        """Calculate duration of the activity in minutes."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 60.0
        return 0.0

    @property
    def duration_hours(self) -> float:
        """Calculate duration of the activity in hours."""
        return self.duration_minutes / 60.0

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "title": self.title,
            "summary": self.summary,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "timelapse_path": self.timelapse_path,
            "duration_minutes": self.duration_minutes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
