from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class BusinessBase(BaseModel):
    name: str
    type: str = "dental"
    address: str = ""
    hours: str = ""
    services: str = ""
    prices: str = ""
    faq: str = ""
    usp: str = ""
    doctors: str = ""
    contact_phone: str = ""


class BusinessCreate(BusinessBase):
    pass


class BusinessOut(BusinessBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class AgentPromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    prompt_text: str
    ghl_field_1: str
    ghl_field_2: str
    ghl_field_3: str
    version: int
    created_at: datetime


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    phone: str
    complaint: str
    status: str
    source: str
    created_at: datetime


class ChatRequest(BaseModel):
    business_id: int
    message: str
    session_id: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str
    patient_created: bool = False