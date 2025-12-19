from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Molecule(Base):
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True, index=True)
    smiles = Column(String(1024), nullable=False)
    generated_for_protein_id = Column(Integer, ForeignKey("proteins.id"), nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=True)  # optional docking/quality score
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    protein = relationship("Protein")
    workspace = relationship("Workspace")
    creator = relationship("User")
