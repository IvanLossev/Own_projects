import logging
import aiohttp
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import SPBU_API_BASE_URL

from keyboards import (
    get_levels_kb,
    get_programs_kb,
    get_years_kb,
    get_periods_kb,
    get_groups_kb,
    get_schedule_nav_kb,
    get_back_kb
)

router = Router()

# Кэш программ в памяти
PROGRAMS_CACHE = {}

async def fetch_api(endpoint: str):
    url = f"{SPBU_API_BASE_URL}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Ошибка API: {response.status} {url}")
                    return None
        except Exception as e:
            logging.error(f"Исключение при запросе {url}: {e}")
            return None

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    msg = await message.answer("⏳ Загружаю актуальные направления с сайта СПбГУ...")
    
    divisions = await fetch_api("/study/divisions")
    if not divisions:
        await msg.edit_text("❌ Не удалось получить список направлений с сервера СПбГУ.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    
    for d in divisions:
        name = d.get("Name") or d.get("name")
        alias = d.get("Alias") or d.get("alias")
        if name and alias:
            builder.button(text=name, callback_data=f"dir_{alias}")
            
    builder.adjust(1)
    
    await msg.edit_text(
        "📚 <b>Добро пожаловать в бот расписания СПбГУ!</b>\n\nВыберите направление обучения из списка:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "back_to_dirs")
async def process_back_to_dirs(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("⏳ Загружаю направления...")
    
    divisions = await fetch_api("/study/divisions")
    if not divisions:
        await callback.message.edit_text("❌ Не удалось загрузить направления.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for d in divisions:
        name = d.get("Name") or d.get("name")
        alias = d.get("Alias") or d.get("alias")
        if name and alias:
            builder.button(text=name, callback_data=f"dir_{alias}")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "📚 Выберите направление обучения:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("dir_"))
async def process_direction_choice(callback: CallbackQuery, state: FSMContext):
    alias = callback.data.split("_", 1)[1]
    await callback.message.edit_text("⏳ Загружаю уровни обучения...")
    
    programs_data = await fetch_api(f"/study/divisions/{alias}/programs/levels")
    
    levels = []
    if isinstance(programs_data, list):
        levels = programs_data
    elif isinstance(programs_data, dict):
        levels = programs_data.get("StudyLevels", []) or programs_data.get("Items", []) or programs_data.get("StudyProgramLevels", [])

    if not levels:
        await callback.message.edit_text(
            "❌ Не удалось загрузить уровни обучения для этого направления. Возможно, API временно недоступно или направление не содержит программ.",
            reply_markup=get_back_kb()
        )
        return

    PROGRAMS_CACHE[alias] = levels
    await state.update_data(alias=alias)
    
    markup = get_levels_kb(alias, levels)
    await callback.message.edit_text(
        "📖 Выберите уровень обучения:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("back_to_levels_"))
async def process_back_to_levels(callback: CallbackQuery, state: FSMContext):
    alias = callback.data.split("_")[3]
    levels = PROGRAMS_CACHE.get(alias, [])
    markup = get_levels_kb(alias, levels)
    await callback.message.edit_text(
        "📖 Выберите уровень обучения:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("lvl_"))
async def process_level_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    alias = parts[1]
    lvl_idx = int(parts[2])
    
    levels = PROGRAMS_CACHE.get(alias, [])
    markup = get_programs_kb(alias, lvl_idx, levels)
    if not markup:
        await callback.message.edit_text("❌ Образовательные программы не найдены.", reply_markup=get_back_kb())
        return
        
    await state.update_data(alias=alias, lvl_idx=lvl_idx)
    await callback.message.edit_text(
        "🎓 Выберите образовательную программу:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("back_to_progs_"))
async def process_back_to_progs(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    alias = parts[3]
    lvl_idx = int(parts[4])
    levels = PROGRAMS_CACHE.get(alias, [])
    markup = get_programs_kb(alias, lvl_idx, levels)
    await callback.message.edit_text(
        "🎓 Выберите образовательную программу:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("prog_"))
async def process_program_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    alias = parts[1]
    lvl_idx = int(parts[2])
    prog_idx = int(parts[3])
    
    levels = PROGRAMS_CACHE.get(alias, [])
    markup = get_years_kb(alias, lvl_idx, prog_idx, levels)
    if not markup:
        await callback.message.edit_text("❌ Годы поступления не найдены.", reply_markup=get_back_kb())
        return
        
    await callback.message.edit_text(
        "📅 Выберите год поступления:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("year_"))
async def process_year_choice(callback: CallbackQuery, state: FSMContext):
    program_id = callback.data.split("_")[1]
    await state.update_data(program_id=program_id)
    
    markup = get_periods_kb(program_id)
    await callback.message.edit_text(
        "📆 Выберите период расписания:",
        reply_markup=markup
    )

@router.callback_query(F.data == "back_to_years_prev")
async def process_back_to_years_prev(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    program_id = data.get("program_id")
    markup = get_periods_kb(program_id)
    await callback.message.edit_text(
        "📆 Выберите период расписания:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("per_"))
async def process_period_choice(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    program_id = parts[1]
    
    await callback.message.edit_text("⏳ Загружаю список учебных групп...")
    
    groups_data = await fetch_api(f"/programs/{program_id}/groups")
    groups = []
    if isinstance(groups_data, list):
        groups = groups_data
    elif isinstance(groups_data, dict):
        groups = groups_data.get("Groups", []) or groups_data.get("StudentGroups", []) or groups_data.get("Items", [])

    if not groups:
        await callback.message.edit_text(
            "❌ Группы не найдены. Возможно, для выбранной программы ещё не сформированы группы или данные временно недоступны.",
            reply_markup=get_back_kb()
        )
        return

    markup = get_groups_kb(groups, program_id)
    await callback.message.edit_text(
        "👥 Выберите вашу учебную группу:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("back_to_periods_"))
async def process_back_to_periods(callback: CallbackQuery, state: FSMContext):
    program_id = callback.data.split("_")[3]
    markup = get_periods_kb(program_id)
    await callback.message.edit_text(
        "📆 Выберите период расписания:",
        reply_markup=markup
    )

@router.callback_query(F.data.startswith("grp_"))
async def process_group_choice(callback: CallbackQuery, state: FSMContext):
    group_id = callback.data.split("_")[1]
    await show_schedule(callback.message, group_id, week_offset=0, edit=True)

@router.callback_query(F.data.startswith("sched_"))
async def process_schedule_pagination(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    group_id = parts[1]
    week_offset = int(parts[2])
    await show_schedule(callback.message, group_id, week_offset=week_offset, edit=True)

async def show_schedule(message: Message, group_id: str, week_offset: int, edit: bool = False):
    if edit:
        await message.edit_text("⏳ Загружаю расписание...")
    else:
        message = await message.answer("⏳ Загружаю расписание...")

    target_date = datetime.now() + timedelta(weeks=week_offset)
    date_str = target_date.strftime("%Y-%m-%d")
    
    schedule_data = await fetch_api(f"/groups/{group_id}/events/{date_str}")
    if not schedule_data or not schedule_data.get("Days"):
        schedule_data = await fetch_api(f"/groups/{group_id}/events")

    if not schedule_data or not schedule_data.get("Days"):
        markup = get_schedule_nav_kb(group_id, week_offset)
        if edit:
            await message.edit_text("На этой неделе занятий нет или расписание не найдено.", reply_markup=markup)
        else:
            await message.answer("На этой неделе занятий нет или расписание не найдено.", reply_markup=markup)
        return

    text = f"📅 <b>Расписание на неделю (от {target_date.strftime('%d.%m.%Y')}):</b>\n\n"
    for day in schedule_data["Days"]:
        text += f"🗓 <b>{day.get('DayString')}</b>\n"
        events = day.get("DayStudyEvents", [])
        if not events:
            text += "<i>Пар нет</i>\n\n"
            continue
        for event in events:
            time = event.get("TimeIntervalString", "")
            subject = event.get("Subject", "")
            educator = event.get("EducatorsDisplayText", "")
            location = event.get("LocationsDisplayText", "")
            text += f"🔹 {time} | <b>{subject}</b>\n👨‍🏫 {educator} | 📍 {location}\n\n"

    if len(text) > 4000:
        text = text[:4000] + "\n... (расписание слишком длинное)"

    markup = get_schedule_nav_kb(group_id, week_offset)
    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)
