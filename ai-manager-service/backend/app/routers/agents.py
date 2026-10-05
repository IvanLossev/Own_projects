from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db
from ..prompt_generator import generate_prompt

router = APIRouter(prefix="/api/businesses", tags=["agents"])


@router.post("/{business_id}/generate-prompt", response_model=schemas.AgentPromptOut)
def generate_business_prompt(business_id: int, db: Session = Depends(get_db)):
    business = crud.get_business(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    result = generate_prompt(business)

    latest = crud.get_latest_prompt(db, business_id)
    next_version = (latest.version + 1) if latest else 1

    data = {
        "business_id": business_id,
        "prompt_text": result["prompt_text"],
        "ghl_field_1": result["ghl_field_1"],
        "ghl_field_2": result["ghl_field_2"],
        "ghl_field_3": result["ghl_field_3"],
        "version": next_version,
    }

    return crud.create_prompt(db, data)


@router.get("/{business_id}/prompt", response_model=schemas.AgentPromptOut)
def get_business_prompt(business_id: int, db: Session = Depends(get_db)):
    business = crud.get_business(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    prompt = crud.get_latest_prompt(db, business_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    return prompt