from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/businesses", tags=["businesses"])


@router.get("", response_model=list[schemas.BusinessOut])
def list_businesses(db: Session = Depends(get_db)):
    return crud.get_businesses(db)


@router.post("", response_model=schemas.BusinessOut)
def create_business(
    payload: schemas.BusinessCreate, db: Session = Depends(get_db)
):
    return crud.create_business(db, payload.model_dump())


@router.get("/{business_id}/patients", response_model=list[schemas.PatientOut])
def list_patients(business_id: int, db: Session = Depends(get_db)):
    business = crud.get_business(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return crud.get_patients(db, business_id)