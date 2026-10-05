from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_levels_kb(alias: str, levels: list):
    """Возвращает клавиатуру с уровнями обучения для конкретного направления"""
    builder = InlineKeyboardBuilder()
    for idx, lvl in enumerate(levels):
        name = lvl.get("StudyLevelName") or lvl.get("Name") or f"Уровень {idx+1}"
        builder.button(text=name, callback_data=f"lvl_{alias}_{idx}")
    builder.button(text="🔙 К направлениям", callback_data="back_to_dirs")
    builder.adjust(1)
    return builder.as_markup()

def get_programs_kb(alias: str, lvl_idx: int, levels: list):
    """Возвращает клавиатуру с образовательными программами"""
    if lvl_idx >= len(levels):
        return None
    
    selected_level = levels[lvl_idx]
    programs = selected_level.get("StudyProgramCombinations", []) or selected_level.get("StudyPrograms", []) or selected_level.get("Programs", [])
    
    if not programs:
        return None
    
    builder = InlineKeyboardBuilder()
    for idx, prog in enumerate(programs[:90]):
        name = prog.get("Name") or prog.get("ProgramName") or f"Программа {idx+1}"
        builder.button(text=name, callback_data=f"prog_{alias}_{lvl_idx}_{idx}")
    builder.button(text="🔙 К уровням", callback_data=f"back_to_levels_{alias}")
    builder.adjust(1)
    return builder.as_markup()

def get_years_kb(alias: str, lvl_idx: int, prog_idx: int, levels: list):
    """Возвращает клавиатуру с годами поступления"""
    if lvl_idx >= len(levels):
        return None
    
    selected_level = levels[lvl_idx]
    programs = selected_level.get("StudyProgramCombinations", []) or selected_level.get("StudyPrograms", []) or selected_level.get("Programs", [])
    
    if prog_idx >= len(programs):
        return None
        
    selected_prog = programs[prog_idx]
    years = selected_prog.get("AdmissionYears", []) or selected_prog.get("Years", [])
    
    if not years:
        return None
    
    builder = InlineKeyboardBuilder()
    for year in years:
        year_name = year.get("YearName") or str(year.get("Year", "Год"))
        prog_id = year.get("StudyProgramId") or year.get("Id")
        if prog_id:
            builder.button(text=year_name, callback_data=f"year_{prog_id}")
            
    builder.button(text="🔙 К программам", callback_data=f"back_to_progs_{alias}_{lvl_idx}")
    builder.adjust(1)
    return builder.as_markup()

def get_periods_kb(program_id: str):
    """Возвращает клавиатуру выбора периода расписания (семестр / учебный год)"""
    builder = InlineKeyboardBuilder()
    now = datetime.now()
    current_year = now.year
    prev_year = current_year - 1
    
    builder.button(text=f"Промежуточная аттестация за предыдущий {prev_year}-{current_year} уч. год", callback_data=f"per_{program_id}_prev")
    builder.button(text=f"Текущий {current_year}-{current_year+1} уч. год", callback_data=f"per_{program_id}_curr")
    builder.button(text="🔙 К годам", callback_data="back_to_years_prev")
    builder.adjust(1)
    return builder.as_markup()

def get_groups_kb(groups: list, program_id: str):
    """Возвращает клавиатуру со списком групп"""
    builder = InlineKeyboardBuilder()
    for group in groups[:90]:
        group_id = group.get("StudentGroupId") or group.get("GroupId") or group.get("Id")
        group_name = group.get("StudentGroupName") or group.get("Name") or "Группа"
        if group_id:
            builder.button(text=group_name, callback_data=f"grp_{group_id}")
    builder.button(text="🔙 К периодам", callback_data=f"back_to_periods_{program_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_schedule_nav_kb(group_id: str, week_offset: int):
    """Возвращает клавиатуру навигации по неделям для расписания группы"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Предыдущая неделя", callback_data=f"sched_{group_id}_{week_offset - 1}")
    builder.button(text="Следующая неделя ➡️", callback_data=f"sched_{group_id}_{week_offset + 1}")
    builder.button(text="🏠 К направлениям", callback_data="back_to_dirs")
    builder.adjust(2, 1)
    return builder.as_markup()

def get_back_kb():
    """Возвращает кнопку возврата к списку направлений"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К направлениям", callback_data="back_to_dirs")
    builder.adjust(1)
    return builder.as_markup()
