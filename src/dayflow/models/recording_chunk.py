"""Recording chunk model - represents 15-second video segments."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from sqlalchemy.orm import relationship
from dayflow.models.database import Base


class RecordingChunk(Base):
    """Model for storing metadata about recorded video chunks."""

    __tablename__ = "recording_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    file_path = Column(String, nullable=False)
    display_id = Column(Integer, default=0, index=True)
    file_size = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<RecordingChunk(id={self.id}, "
            f"start={self.start_time}, end={self.end_time}, "
            f"display={self.display_id})>"
        )

    @property
    def duration_seconds(self) -> float:
        """Calculate duration of the chunk in seconds."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds()
        return 0.0

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "file_path": self.file_path,
            "display_id": self.display_id,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
