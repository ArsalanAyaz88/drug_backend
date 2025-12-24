from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class PipelineJob(Base):
    __tablename__ = "pipeline_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    protein_id = Column(Integer, ForeignKey("proteins.id"), nullable=False)
    status = Column(String(32), default="queued", nullable=False)
    current_step = Column(String(64), nullable=True)
    strategy = Column(String(32), nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(String(512), nullable=True)
    results = Column(Text, nullable=True)  # JSON-serialized summary
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User")
    protein = relationship("Protein")
