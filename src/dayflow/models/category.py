"""Timeline category model - for categorizing activities."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from dayflow.models.database import Base


class TimelineCategory(Base):
    """Model for activity categories."""

    __tablename__ = "timeline_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    color = Column(String, nullable=False)  # Hex color code
    icon = Column(String, nullable=True)  # Emoji or icon name
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to activities
    activities = relationship(
        "TimelineActivity",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TimelineCategory(id={self.id}, name='{self.name}', color='{self.color}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "icon": self.icon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def get_default_categories() -> list[dict]:
        """Get list of default categories."""
        return [
            {"name": "工作", "color": "#4CAF50", "icon": "💼"},
            {"name": "会议", "color": "#2196F3", "icon": "👥"},
            {"name": "休息", "color": "#FF9800", "icon": "☕"},
            {"name": "效率", "color": "#9C27B0", "icon": "📝"},
            {"name": "学习", "color": "#00BCD4", "icon": "📚"},
            {"name": "娱乐", "color": "#F44336", "icon": "🎮"},
        ]
