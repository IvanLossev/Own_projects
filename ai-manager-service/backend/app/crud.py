import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from . import models


def get_businesses(db: Session) -> List[models.Business]:
    return db.query(models.Business).order_by(models.Business.id).all()


def get_business(db: Session, business_id: int) -> Optional[models.Business]:
    return db.query(models.Business).filter(models.Business.id == business_id).first()


def create_business(db: Session, data: dict) -> models.Business:
    business = models.Business(**data)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def get_latest_prompt(db: Session, business_id: int) -> Optional[models.AgentPrompt]:
    return (
        db.query(models.AgentPrompt)
        .filter(models.AgentPrompt.business_id == business_id)
        .order_by(models.AgentPrompt.version.desc())
        .first()
    )


def create_prompt(db: Session, data: dict) -> models.AgentPrompt:
    prompt = models.AgentPrompt(**data)
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt


def get_session(db: Session, session_id: str) -> Optional[models.Session]:
    return db.query(models.Session).filter(models.Session.id == session_id).first()


def get_patient(db: Session, patient_id: int) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()


def create_session(db: Session, data: dict) -> models.Session:
    session = models.Session(**data)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session(db: Session, session: models.Session, data: dict) -> models.Session:
    for key, value in data.items():
        setattr(session, key, value)
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def get_session_history(session: models.Session) -> List[dict]:
    try:
        return json.loads(session.history or "[]")
    except json.JSONDecodeError:
        return []


def set_session_history(db: Session, session: models.Session, history: List[dict]):
    session.history = json.dumps(history, ensure_ascii=False)
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)


def create_log(db: Session, data: dict) -> models.Log:
    log = models.Log(**data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_patients(db: Session, business_id: int) -> List[models.Patient]:
    return (
        db.query(models.Patient)
        .filter(models.Patient.business_id == business_id)
        .order_by(models.Patient.created_at.desc())
        .all()
    )


def get_patient_by_phone(
    db: Session, business_id: int, phone: str
) -> Optional[models.Patient]:
    return (
        db.query(models.Patient)
        .filter(
            models.Patient.business_id == business_id,
            models.Patient.phone == phone,
        )
        .first()
    )


def create_patient(db: Session, data: dict) -> models.Patient:
    patient = models.Patient(**data)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient: models.Patient, data: dict) -> models.Patient:
    for key, value in data.items():
        setattr(patient, key, value)
    db.commit()
    db.refresh(patient)
    return patient