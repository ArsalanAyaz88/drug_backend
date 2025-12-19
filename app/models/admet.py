from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class AdmetResult(Base):
    __tablename__ = "admet_results"

    id = Column(Integer, primary_key=True, index=True)
    molecule_id = Column(Integer, ForeignKey("molecules.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    solubility = Column(Float, nullable=True)
    toxicity = Column(Float, nullable=True)
    clearance = Column(Float, nullable=True)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    molecule = relationship("Molecule")
    user = relationship("User")
