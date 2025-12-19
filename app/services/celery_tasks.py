from __future__ import annotations
from typing import Optional

from app.services.celery_app import get_celery
from app.services.tasks import task_run_docking, task_run_admet

_app = get_celery()

if _app:
    @_app.task(name="druggenix.run_docking")
    def run_docking(dock_job_id: int) -> None:
        task_run_docking(dock_job_id)

    @_app.task(name="druggenix.run_admet")
    def run_admet(molecule_id: int, user_id: int) -> Optional[int]:
        return task_run_admet(molecule_id, user_id)
