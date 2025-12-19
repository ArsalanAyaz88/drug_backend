from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class DockJob(Base):
    __tablename__ = "dock_jobs"

    id = Column(Integer, primary_key=True, index=True)
    protein_id = Column(Integer, ForeignKey("proteins.id"), nullable=False)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), default="completed", nullable=False)
    score = Column(Float, nullable=True)
    pose_path = Column(String(512), nullable=True)  # e.g., SDF/PDBQT path
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    protein = relationship("Protein")
    molecule = relationship("Molecule")
    user = relationship("User")
