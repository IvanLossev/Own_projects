import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from backend.app import crud
from backend.app.agent_engine import OpenRouterError, extract_patient_info, get_bot_response
from backend.app.config import settings
from backend.app.database import SessionLocal

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def admin_chat_id() -> str:
    return str(settings.TELEGRAM_ADMIN_CHAT_ID).strip()


def is_admin(update: Update) -> bool:
    return bool(update.effective_chat and str(update.effective_chat.id) == admin_chat_id())


def session_chat_id(session_id: str) -> int:
    return int(session_id.removeprefix("telegram:"))


def human_keyboard(session_id: str, human_taken: bool = False) -> InlineKeyboardMarkup:
    action = "bot" if human_taken else "human"
    label = "Вернуть боту" if human_taken else "Взять диалог"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=f"{action}:{session_id}")]]
    )


def get_or_create_session(db, chat_id: int):
    session_id = f"telegram:{chat_id}"
    session = crud.get_session(db, session_id)
    if session is None:
        business = crud.get_businesses(db)[0]
        session = crud.create_session(
            db,
            {
                "id": session_id,
                "business_id": business.id,
                "channel": "telegram",
                "status": "BOT_ACTIVE",
            },
        )
    return session


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, session, message: str, response: str):
    if not admin_chat_id():
        return
    await context.bot.send_message(
        chat_id=admin_chat_id(),
        text=(
            f"Telegram-сессия: {session.id}\n"
            f"Клиент: {message}\n\n"
            f"Ответ бота: {response}"
        ),
        reply_markup=human_keyboard(session.id, session.status == "HUMAN_TAKEN"),
    )


def format_history(history: list[dict]) -> str:
    labels = {"user": "Клиент", "assistant": "Бот"}
    lines = []
    for item in history:
        label = "Администратор" if item.get("author") == "operator" else labels.get(
            item.get("role"), "Сообщение"
        )
        lines.append(f"{label}: {item.get('content', '')}")
    return "\n\n".join(lines) or "История пока пустая."


async def notify_admin_of_client_message(context: ContextTypes.DEFAULT_TYPE, session, message: str):
    if not admin_chat_id():
        return
    await context.bot.send_message(
        chat_id=admin_chat_id(),
        text=f"Новое сообщение клиента в {session.id}:\n\nКлиент: {message}",
        reply_markup=human_keyboard(session.id, True),
    )


def split_pending_messages(history: list[dict]) -> tuple[list[dict], list[str]]:
    last_assistant = max(
        (index for index, item in enumerate(history) if item.get("role") == "assistant"),
        default=-1,
    )
    completed_history = history[: last_assistant + 1]
    pending = [
        item["content"]
        for item in history[last_assistant + 1 :]
        if item.get("role") == "user" and item.get("content")
    ]
    return completed_history, pending


def save_patient_profile(db, session, info: dict):
    patient = (
        crud.get_patient(db, session.patient_id)
        if session.patient_id is not None
        else None
    )
    if patient is None and info.get("phone"):
        patient = crud.get_patient_by_phone(
            db, session.business_id, info["phone"]
        )
        if patient:
            crud.update_session(db, session, {"patient_id": patient.id})

    if patient:
        changed_fields = []
        updates = {}
        for field in ("name", "phone"):
            value = info.get(field, "")
            if value and value != getattr(patient, field):
                updates[field] = value
                changed_fields.append(field)
        complaint = info.get("complaint", "")
        if complaint and complaint != patient.complaint:
            updates["complaint"] = complaint
        if updates:
            crud.update_patient(db, patient, updates)
        return patient, changed_fields, True

    if info.get("name") and info.get("phone"):
        patient = crud.create_patient(
            db,
            {
                "business_id": session.business_id,
                "name": info["name"],
                "phone": info["phone"],
                "complaint": info.get("complaint", ""),
                "status": "new",
                "source": "telegram",
            },
        )
        crud.update_session(db, session, {"patient_id": patient.id})
        return patient, ["name", "phone"], False
    return None, [], False


async def notify_admin_of_profile_change(context, session, patient, fields, existing):
    if not patient or not fields or not admin_chat_id():
        return
    russian_fields = {"name": "имя", "phone": "телефон"}
    status = (
        "изменены " + " и ".join(russian_fields[field] for field in fields)
        if existing
        else "собраны имя и телефон"
    )
    await context.bot.send_message(
        chat_id=admin_chat_id(),
        text=(
            f"В сессии {session.id} {status}.\n"
            f"Имя: {patient.name}\n"
            f"Телефон: {patient.phone}\n"
            f"Интересующая услуга / запрос: {patient.complaint or 'не указан'}"
        ),
    )


async def handle_client_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message or not update.message.text:
        return
    if is_admin(update):
        return

    db = SessionLocal()
    try:
        session = get_or_create_session(db, update.effective_chat.id)
        if session.status == "HUMAN_TAKEN":
            user_message = update.message.text
            history = crud.get_session_history(session)
            history.append({"role": "user", "content": user_message})
            crud.set_session_history(db, session, history)
            crud.create_log(
                db,
                {
                    "session_id": session.id,
                    "user_message": user_message,
                    "agent_response": "[human operator mode]",
                    "tokens_used": 0,
                },
            )
            dialog_text = "\n".join(
                f"{item.get('role', '')}: {item.get('content', '')}"
                for item in history
            )
            try:
                info = await extract_patient_info(dialog_text)
            except Exception:
                info = {"name": "", "phone": "", "complaint": ""}
            patient, changed_fields, existing = save_patient_profile(
                db, session, info
            )
            await update.message.reply_text(
                "Ваш диалог передан администратору. Он ответит в ближайшее время."
            )
            await notify_admin_of_client_message(
                context, session, user_message
            )
            await notify_admin_of_profile_change(
                context, session, patient, changed_fields, existing
            )
            return

        prompt = crud.get_latest_prompt(db, session.business_id)
        system_prompt = prompt.prompt_text if prompt else ""
        known_patient = (
            crud.get_patient(db, session.patient_id)
            if session.patient_id is not None
            else None
        )
        if known_patient and known_patient.name and known_patient.phone:
            system_prompt += (
                "\n\nСОХРАНЁННЫЕ ДАННЫЕ ПОСТОЯННОГО КЛИЕНТА\n"
                f"Имя: {known_patient.name}\nТелефон: {known_patient.phone}\n"
                "Если клиент снова явно хочет записаться и вы уже уточнили его "
                "пожелания, не проси имя и телефон заново. Спроси одним вопросом, "
                "актуальны ли сохранённые имя и телефон. Если клиент подтвердит, "
                "поблагодари и сообщи, что передашь заявку администратору. Если "
                "клиент исправит одно из значений, используй новое значение и "
                "уточни только недостающие или изменённые данные. Не показывай эти "
                "данные в ответах на вопросы, не связанные с записью."
            )
        history = crud.get_session_history(session)
        user_message = update.message.text

        try:
            bot_result = await get_bot_response(system_prompt, history, user_message)
            bot_response = bot_result["content"]
            tokens_used = bot_result["tokens"]
        except OpenRouterError as exc:
            await update.message.reply_text(str(exc))
            return

        dialog_text = "\n".join(
            [f"{item.get('role', '')}: {item.get('content', '')}" for item in history]
            + [f"user: {user_message}", f"assistant: {bot_response}"]
        )
        try:
            info = await extract_patient_info(dialog_text)
        except Exception:
            info = {"name": "", "phone": "", "complaint": ""}

        patient, changed_fields, patient_was_existing = save_patient_profile(
            db, session, info
        )

        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": bot_response},
            ]
        )
        crud.set_session_history(db, session, history)
        crud.create_log(
            db,
            {
                "session_id": session.id,
                "user_message": user_message,
                "agent_response": bot_response,
                "tokens_used": tokens_used,
            },
        )
        await update.message.reply_text(bot_response)
        await notify_admin(context, session, user_message, bot_response)
        await notify_admin_of_profile_change(
            context, session, patient, changed_fields, patient_was_existing
        )
    finally:
        db.close()


async def handle_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if not is_admin(update):
        await query.answer("Недоступно", show_alert=True)
        return

    await query.answer()
    action, session_id = query.data.split(":", 1)
    db = SessionLocal()
    try:
        session = crud.get_session(db, session_id)
        if not session:
            await query.edit_message_text("Сессия не найдена")
            return
        new_status = "HUMAN_TAKEN" if action == "human" else "BOT_ACTIVE"
        crud.update_session(db, session, {"status": new_status})
        if action == "human":
            text = "Режим оператора включён. Используйте /reply CHAT_ID текст."
            history_text = format_history(crud.get_session_history(session))
            await context.bot.send_message(
                chat_id=admin_chat_id(),
                text=f"История сессии {session_id}:\n\n{history_text}",
            )
        else:
            history = crud.get_session_history(session)
            completed_history, pending_messages = split_pending_messages(history)
            if pending_messages:
                prompt = crud.get_latest_prompt(db, session.business_id)
                system_prompt = prompt.prompt_text if prompt else ""
                for index, pending_message in enumerate(pending_messages):
                    try:
                        result = await get_bot_response(
                            system_prompt, completed_history, pending_message
                        )
                    except OpenRouterError as exc:
                        remaining_history = completed_history + [
                            {"role": "user", "content": message}
                            for message in pending_messages[index:]
                        ]
                        crud.set_session_history(db, session, remaining_history)
                        crud.update_session(
                            db, session, {"status": "HUMAN_TAKEN"}
                        )
                        text = (
                            "Не удалось обработать ожидающие сообщения. "
                            f"Диалог оставлен в режиме оператора: {exc}"
                        )
                        await context.bot.send_message(
                            chat_id=admin_chat_id(), text=text
                        )
                        await query.edit_message_reply_markup(
                            reply_markup=human_keyboard(session_id, True)
                        )
                        return

                    bot_response = result["content"]
                    completed_history.extend(
                        [
                            {"role": "user", "content": pending_message},
                            {"role": "assistant", "content": bot_response},
                        ]
                    )
                    crud.set_session_history(db, session, completed_history)
                    crud.create_log(
                        db,
                        {
                            "session_id": session.id,
                            "user_message": pending_message,
                            "agent_response": bot_response,
                            "tokens_used": result["tokens"],
                        },
                    )
                    await context.bot.send_message(
                        chat_id=session_chat_id(session_id), text=bot_response
                    )
                text = "Режим бота включён. Бот ответил на сообщения, ожидавшие ответа."
            else:
                text = "Режим бота включён. Следующее сообщение обработает ИИ."
            crud.update_session(db, session, {"status": "BOT_ACTIVE"})
        await query.edit_message_reply_markup(
            reply_markup=human_keyboard(session_id, action == "human")
        )
        await context.bot.send_message(chat_id=admin_chat_id(), text=text)
        await context.bot.send_message(
            chat_id=session_chat_id(session_id),
            text=(
                "К диалогу подключился администратор."
                if action == "human"
                else "Диалог снова передан ИИ-администратору."
            ),
        )
    finally:
        db.close()


async def reply_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or not update.message:
        return
    parts = update.message.text.split(maxsplit=2)
    if len(parts) < 3:
        await update.message.reply_text("Формат: /reply CHAT_ID текст ответа")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await update.message.reply_text("CHAT_ID должен быть числом")
        return
    db = SessionLocal()
    try:
        session = crud.get_session(db, f"telegram:{chat_id}")
        if not session:
            await update.message.reply_text("Сессия клиента не найдена")
            return
        history = crud.get_session_history(session)
        operator_message = parts[2]
        history.append(
            {"role": "assistant", "author": "operator", "content": operator_message}
        )
        crud.set_session_history(db, session, history)
        crud.create_log(
            db,
            {
                "session_id": session.id,
                "user_message": "[operator]",
                "agent_response": operator_message,
                "tokens_used": 0,
            },
        )
    finally:
        db.close()
    await context.bot.send_message(chat_id=chat_id, text=parts[2])
    await update.message.reply_text("Ответ отправлен клиенту")


async def new_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or is_admin(update):
        return
    db = SessionLocal()
    try:
        session = get_or_create_session(db, update.effective_chat.id)
        crud.update_session(
            db,
            session,
            {"history": "[]", "status": "BOT_ACTIVE"},
        )
    finally:
        db.close()
    await update.message.reply_text("Начинаем новую переписку. История предыдущего диалога сохранена.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update):
        await update.message.reply_text(
            "Вы администратор. Для ручного ответа используйте /reply CHAT_ID текст."
        )
    else:
        await update.message.reply_text("Здравствуйте! Напишите ваш вопрос, и я помогу.")


def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан в .env")
    if not admin_chat_id():
        raise RuntimeError("TELEGRAM_ADMIN_CHAT_ID не задан в .env")

    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new", new_dialog))
    application.add_handler(CommandHandler("reply", reply_to_client))
    application.add_handler(CallbackQueryHandler(handle_mode_callback, pattern=r"^(human|bot):"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_client_message))
    logger.info("Telegram bot is running")
    application.run_polling()


if __name__ == "__main__":
    main()
