from app.db.base_class import Base

# Import all models here so Alembic/metadata can see them
from app.models.user import User  # noqa: F401
from app.models.workspace import Workspace  # noqa: F401
from app.models.protein import Protein  # noqa: F401
from app.models.molecule import Molecule  # noqa: F401
from app.models.dock_job import DockJob  # noqa: F401
from app.models.admet import AdmetResult  # noqa: F401
from app.models.pipeline_job import PipelineJob  # noqa: F401
from app.models.setting import Setting  # noqa: F401
