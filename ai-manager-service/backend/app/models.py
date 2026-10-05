import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, default="dental")
    address = Column(Text, default="")
    hours = Column(Text, default="")
    services = Column(Text, default="")
    prices = Column(Text, default="")
    faq = Column(Text, default="")
    usp = Column(Text, default="")
    doctors = Column(Text, default="")
    contact_phone = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    prompts = relationship("AgentPrompt", back_populates="business")
    patients = relationship("Patient", back_populates="business")
    sessions = relationship("Session", back_populates="business")


class AgentPrompt(Base):
    __tablename__ = "agent_prompts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    prompt_text = Column(Text, default="")
    ghl_field_1 = Column(Text, default="")
    ghl_field_2 = Column(Text, default="")
    ghl_field_3 = Column(Text, default="")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="prompts")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    name = Column(String, default="")
    phone = Column(String, default="")
    complaint = Column(Text, default="")
    status = Column(String, default="new")
    source = Column(String, default="chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="patients")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    channel = Column(String, default="demo")
    status = Column(String, default="BOT_ACTIVE")
    history = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="sessions")
    logs = relationship("Log", back_populates="session")


class Log(Base):
    __tablename__ = "logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    user_message = Column(Text, default="")
    agent_response = Column(Text, default="")
    tokens_used = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="logs")