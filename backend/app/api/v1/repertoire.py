"""Repertoire endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.models import Repertoire
from app.core.schemas import (
    RepertoireCreate,
    RepertoireDetailOut,
    RepertoireLineCreate,
    RepertoireLineOut,
    RepertoireLineUpdate,
    RepertoireOut,
    RepertoireUpdate,
)
from app.services.repertoire import storage

router = APIRouter(prefix="/repertoire", tags=["repertoire"])


@router.get("", response_model=list[RepertoireOut])
def list_repertoires(db: Session = Depends(get_db)) -> list[RepertoireOut]:
    reps = storage.list_repertoires(db)
    return [RepertoireOut.model_validate(r) for r in reps]


@router.post("", response_model=RepertoireOut, status_code=status.HTTP_201_CREATED)
def create_repertoire(payload: RepertoireCreate, db: Session = Depends(get_db)) -> RepertoireOut:
    rep = storage.create_repertoire(db, payload)
    return RepertoireOut.model_validate(rep)


@router.get("/{repertoire_id}", response_model=RepertoireDetailOut)
def get_repertoire(repertoire_id: str, db: Session = Depends(get_db)) -> RepertoireDetailOut:
    rep = storage.get_repertoire(db, repertoire_id)
    if rep is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    lines = storage.list_lines(db, repertoire_id)
    detail = RepertoireDetailOut.model_validate(rep)
    detail.lines = [RepertoireLineOut.model_validate(l) for l in lines]
    return detail


@router.put("/{repertoire_id}", response_model=RepertoireOut)
def update_repertoire(
    repertoire_id: str, payload: RepertoireUpdate, db: Session = Depends(get_db)
) -> RepertoireOut:
    rep = storage.update_repertoire(db, repertoire_id, payload)
    if rep is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    return RepertoireOut.model_validate(rep)


@router.delete("/{repertoire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repertoire(repertoire_id: str, db: Session = Depends(get_db)) -> Response:
    if not storage.delete_repertoire(db, repertoire_id):
        raise HTTPException(status_code=404, detail="Repertoire not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/line", response_model=RepertoireLineOut, status_code=status.HTTP_201_CREATED)
def add_line(payload: RepertoireLineCreate, db: Session = Depends(get_db)) -> RepertoireLineOut:
    if storage.get_repertoire(db, payload.repertoire_id) is None:
        raise HTTPException(status_code=404, detail="Repertoire not found")
    line = storage.create_line(db, payload)
    return RepertoireLineOut.model_validate(line)


@router.put("/line/{line_id}", response_model=RepertoireLineOut)
def update_line(
    line_id: str, payload: RepertoireLineUpdate, db: Session = Depends(get_db)
) -> RepertoireLineOut:
    line = storage.update_line(db, line_id, payload)
    if line is None:
        raise HTTPException(status_code=404, detail="Line not found")
    return RepertoireLineOut.model_validate(line)


@router.delete("/line/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line(line_id: str, db: Session = Depends(get_db)) -> Response:
    if not storage.delete_line(db, line_id):
        raise HTTPException(status_code=404, detail="Line not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
