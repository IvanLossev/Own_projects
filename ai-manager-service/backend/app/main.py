from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from . import models
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import agents, businesses, chat


def ensure_schema():
    with engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(businesses)")).all()
        if not any(column[1] == "doctors" for column in columns):
            connection.execute(
                text("ALTER TABLE businesses ADD COLUMN doctors TEXT DEFAULT ''")
            )


def seed_businesses():
    db = SessionLocal()
    try:
        if db.query(models.Business).count() == 0:
            db.add(
                models.Business(
                    name="Дента-Плюс",
                    type="dental",
                    address="г. Алматы, ул. Абая 10",
                    hours="Пн-Сб: 9:00 - 20:00, Вс: выходной",
                    services="Лечение кариеса, имплантация, отбеливание, протезирование",
                    prices=(
                        "Консультация - 5000 тг\n"
                        "Лечение кариеса - от 15000 тг\n"
                        "Имплантация - от 180000 тг\n"
                        "Отбеливание - от 45000 тг\n"
                        "Протезирование - от 120000 тг"
                    ),
                    faq="Работаем по записи. Принимаем карты.",
                    usp="Безболезненное лечение, гарантия 2 года",
                    doctors=(
                        "Доктор Айболит\n"
                        "Доктор Стрэндж\n"
                        "Доктор Хаус\n"
                        "Доктор Ватсон\n"
                        "Доктор Кто"
                    ),
                    contact_phone="+7 700 123 45 67",
                )
            )
            db.commit()
        else:
            business = (
                db.query(models.Business)
                .filter(models.Business.name == "Дента-Плюс")
                .first()
            )
            if business and not business.doctors:
                business.doctors = (
                    "Доктор Айболит\n"
                    "Доктор Стрэндж\n"
                    "Доктор Хаус\n"
                    "Доктор Ватсон\n"
                    "Доктор Кто"
                )
                business.prices = (
                    "Консультация - 5000 тг\n"
                    "Лечение кариеса - от 15000 тг\n"
                    "Имплантация - от 180000 тг\n"
                    "Отбеливание - от 45000 тг\n"
                    "Протезирование - от 120000 тг"
                )
                db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    seed_businesses()
    yield


app = FastAPI(title="AI-Manager Service", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

app.include_router(businesses.router)
app.include_router(agents.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return RedirectResponse(url="/static/demo.html")