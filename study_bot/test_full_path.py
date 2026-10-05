"""
Тестовый скрипт для проверки полного пути пользователя через API СПбГУ.
Пробует найти активные группы (свежие годы), чтобы протестировать расписание.
"""
import asyncio
import aiohttp
from config import SPBU_API_BASE_URL

async def fetch(session, endpoint, timeout=30):
    url = f"{SPBU_API_BASE_URL}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    async with session.get(url, headers=headers, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return await resp.json()

async def main():
    async with aiohttp.ClientSession() as session:
        print("=" * 60)
        print("STEP 1: Получение направлений")
        divisions = await fetch(session, "/study/divisions")
        print(f"✅ Найдено {len(divisions)} направлений")
        
        alias = "MATH"
        division = next((d for d in divisions if d.get("Alias") == alias), None)
        print(f"✅ Выбрано: {division['Name']} (alias={alias})")
        
        print("\n" + "=" * 60)
        print("STEP 2: Получение уровней обучения")
        levels = await fetch(session, f"/study/divisions/{alias}/programs/levels")
        print(f"✅ Найдено {len(levels)} уровней")
        
        # Ищем первый год с группами
        found_groups = None
        found_program_id = None
        found_year_name = None
        
        for lvl_idx, selected_level in enumerate(levels):
            programs = selected_level.get("StudyProgramCombinations", []) or selected_level.get("StudyPrograms", []) or selected_level.get("Programs", [])
            print(f"\nУровень [{lvl_idx}]: {selected_level.get('StudyLevelName')} — {len(programs)} программ")
            
            for prog_idx, selected_prog in enumerate(programs):
                years = selected_prog.get("AdmissionYears", []) or selected_prog.get("Years", [])
                if not years:
                    continue
                # Сортируем годы по убыванию, берём самые свежие
                sorted_years = sorted(years, key=lambda y: y.get("YearNumber", 0) or y.get("Year", 0), reverse=True)
                for year in sorted_years[:3]:  # пробуем 3 свежих года
                    program_id = year.get("StudyProgramId")
                    year_name = year.get("YearName")
                    print(f"  Пробуем program_id={program_id} ({year_name}) из '{selected_prog.get('Name', '')[:50]}'...")
                    try:
                        groups_data = await fetch(session, f"/programs/{program_id}/groups")
                        groups = groups_data.get("Groups", []) if isinstance(groups_data, dict) else groups_data
                        if groups:
                            found_groups = groups
                            found_program_id = program_id
                            found_year_name = year_name
                            print(f"   ✅ НАЙДЕНО {len(groups)} групп!")
                            break
                        else:
                            print(f"   0 групп")
                    except Exception as e:
                        print(f"   Ошибка: {e}")
                if found_groups:
                    break
            if found_groups:
                break
        
        if not found_groups:
            print("❌ Не удалось найти группы ни для одной программы!")
            return
        
        print(f"\n✅ Используем program_id={found_program_id}, год={found_year_name}")
        
        group = found_groups[0]
        group_id = group.get("StudentGroupId") or group.get("GroupId") or group.get("Id")
        print(f"✅ Выбрана группа: {group.get('StudentGroupName')} (id={group_id})")
        
        print("\n" + "=" * 60)
        print("STEP 3: Получение расписания")
        schedule = await fetch(session, f"/groups/{group_id}/events")
        days = schedule.get("Days", [])
        print(f"✅ Расписание получено. Неделя: {schedule.get('WeekDisplayText')}")
        print(f"✅ Дней с занятиями: {len(days)}")
        
        for day in days:
            print(f"\n🗓 {day.get('DayString')}")
            events = day.get("DayStudyEvents", [])
            if not events:
                print("   <Пар нет>")
            for ev in events:
                time = ev.get("TimeIntervalString", "")
                subject = ev.get("Subject", "")
                educator = ev.get("EducatorsDisplayText", "")
                location = ev.get("LocationsDisplayText", "")
                print(f"   🔹 {time} | {subject}")
                print(f"      👨‍🏫 {educator} | 📍 {location}")
        
        print("\n" + "=" * 60)
        print("🎉 ПОЛНЫЙ ПУТЬ ПРОЙДЁН УСПЕШНО!")

if __name__ == "__main__":
    asyncio.run(main())
