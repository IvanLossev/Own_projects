from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..agent_engine import OpenRouterError, extract_patient_info, get_bot_response
from ..database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/demo", response_model=schemas.ChatResponse)
async def demo_chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    business = crud.get_business(db, payload.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    session = crud.get_session(db, payload.session_id)

    if session is None:
        session = crud.create_session(
            db,
            {
                "id": payload.session_id,
                "business_id": payload.business_id,
                "channel": "demo",
                "status": "BOT_ACTIVE",
            },
        )

    if session.status == "HUMAN_TAKEN":
        return schemas.ChatResponse(
            session_id=session.id,
            response="Диалог перехвачен оператором",
            status=session.status,
            patient_created=False,
        )

    prompt = crud.get_latest_prompt(db, payload.business_id)
    system_prompt = prompt.prompt_text if prompt else ""

    history = crud.get_session_history(session)

    try:
        bot_result = await get_bot_response(system_prompt, history, payload.message)
    except OpenRouterError as exc:
        return schemas.ChatResponse(
            session_id=session.id,
            response=str(exc),
            status="BOT_ERROR",
            patient_created=False,
        )
    bot_response = bot_result["content"]
    tokens_used = bot_result["tokens"]

    patient_created = False
    dialog_text = "\n".join(
        [f"{m.get('role', '')}: {m.get('content', '')}" for m in history]
        + [f"user: {payload.message}", f"assistant: {bot_response}"]
    )

    try:
        info = await extract_patient_info(dialog_text)
    except Exception:
        info = {"name": "", "phone": "", "complaint": ""}

    if info.get("name") and info.get("phone"):
        existing = crud.get_patient_by_phone(
            db, payload.business_id, info["phone"]
        )
        if existing:
            crud.update_patient(
                db,
                existing,
                {
                    "name": info["name"],
                    "complaint": info.get("complaint") or existing.complaint,
                },
            )
        else:
            patient = crud.create_patient(
                db,
                {
                    "business_id": payload.business_id,
                    "name": info["name"],
                    "phone": info["phone"],
                    "complaint": info.get("complaint", ""),
                    "status": "new",
                    "source": "chat",
                },
            )
            crud.update_session(db, session, {"patient_id": patient.id})
        patient_created = True

    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": bot_response})
    crud.set_session_history(db, session, history)

    crud.create_log(
        db,
        {
            "session_id": session.id,
            "user_message": payload.message,
            "agent_response": bot_response,
            "tokens_used": tokens_used,
        },
    )

    return schemas.ChatResponse(
        session_id=session.id,
        response=bot_response,
        status=session.status,
        patient_created=patient_created,
    )