import asyncio
import aiohttp
import json
from config import SPBU_API_BASE_URL

async def fetch(session, endpoint, verbose=True):
    url = f"{SPBU_API_BASE_URL}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if verbose:
                print(f">>> GET {url} -> {resp.status}")
            if resp.status == 200:
                return await resp.json()
            else:
                if verbose:
                    print(f"   Error: {await resp.text()[:300]}")
                return None
    except Exception as e:
        if verbose:
            print(f"   Exception: {e}")
        return None

async def main():
    async with aiohttp.ClientSession() as session:
        # Get programs for MATH
        print("Getting programs for MATH...")
        prog_data = await fetch(session, "/study/divisions/MATH/programs/levels", verbose=False)
        if not prog_data:
            print("Failed")
            return
        
        # Collect all program IDs with year info
        program_candidates = []
        for lvl in prog_data:
            lvl_name = lvl.get("StudyLevelName", "")
            for combo in lvl.get("StudyProgramCombinations", []):
                combo_name = combo.get("Name", "")
                for year in combo.get("AdmissionYears", []):
                    pid = year.get("StudyProgramId")
                    year_name = year.get("YearName")
                    if pid:
                        program_candidates.append({
                            "pid": pid,
                            "year": year_name,
                            "level": lvl_name,
                            "combo": combo_name
                        })
        
        print(f"Found {len(program_candidates)} program/year combinations")
        
        # Try groups for each program, prioritizing recent years
        program_candidates.sort(key=lambda x: x.get("year", ""), reverse=True)
        
        found_groups = None
        found_pid = None
        for cand in program_candidates[:15]:
            pid = cand["pid"]
            print(f"\nTrying groups for program_id={pid} ({cand['year']}, {cand['combo'][:50]})...")
            groups_data = await fetch(session, f"/programs/{pid}/groups", verbose=False)
            if groups_data and isinstance(groups_data, dict):
                groups_list = groups_data.get("Groups", [])
                print(f"  Response keys: {list(groups_data.keys())}, Groups count: {len(groups_list)}")
                if groups_list:
                    print(f"  First group keys: {list(groups_list[0].keys())}")
                    print(f"  First group: {json.dumps(groups_list[0], ensure_ascii=False, indent=2)[:600]}")
                    found_groups = groups_data
                    found_pid = pid
                    break
            elif groups_data and isinstance(groups_data, list):
                print(f"  List response, count: {len(groups_data)}")
                if groups_data:
                    print(f"  First: {json.dumps(groups_data[0], ensure_ascii=False, indent=2)[:400]}")
                    found_groups = groups_data
                    found_pid = pid
                    break
        
        if not found_groups:
            print("\nNo groups found for any program! Trying other divisions...")
            aliases = ["PHYS", "ECON", "CHEM", "LAW", "HIST", "BIOL", "PHIL", "MGMT"]
            for alias in aliases:
                print(f"\nTrying division {alias}...")
                div_progs = await fetch(session, f"/study/divisions/{alias}/programs/levels", verbose=False)
                if not div_progs:
                    continue
                for lvl in div_progs:
                    for combo in lvl.get("StudyProgramCombinations", []):
                        for year in combo.get("AdmissionYears", []):
                            pid = year.get("StudyProgramId")
                            if pid:
                                groups_data = await fetch(session, f"/programs/{pid}/groups", verbose=False)
                                if groups_data and isinstance(groups_data, dict):
                                    groups_list = groups_data.get("Groups", [])
                                    if groups_list:
                                        print(f"FOUND in {alias}! pid={pid}")
                                        found_groups = groups_data
                                        found_pid = pid
                                        break
                                elif groups_data and isinstance(groups_data, list) and groups_data:
                                    print(f"FOUND in {alias}! pid={pid}")
                                    found_groups = groups_data
                                    found_pid = pid
                                    break
                        if found_groups: break
                    if found_groups: break
                if found_groups: break
        
        if not found_groups:
            print("Still no groups found anywhere!")
            return
        
        with open("groups_response.json", "w", encoding="utf-8") as f:
            json.dump(found_groups, f, ensure_ascii=False, indent=2)
        
        # Extract group ID
        group_id = None
        group_name = None
        if isinstance(found_groups, dict):
            groups_list = found_groups.get("Groups", [])
        else:
            groups_list = found_groups
        
        for g in groups_list:
            gid = g.get("StudentGroupId") or g.get("GroupId") or g.get("Id")
            if gid:
                group_id = gid
                group_name = g.get("StudentGroupName") or g.get("Name") or "Unknown"
                print(f"\nFound group_id={group_id}, name={group_name}")
                break
        
        if not group_id:
            print("No group ID found in groups list!")
            return
        
        # Get schedule
        print("\n--- Schedule ---")
        sched_data = await fetch(session, f"/groups/{group_id}/events")
        if sched_data:
            with open("schedule_response.json", "w", encoding="utf-8") as f:
                json.dump(sched_data, f, ensure_ascii=False, indent=2)
            if isinstance(sched_data, dict):
                print(f"Keys: {list(sched_data.keys())}")
                days = sched_data.get("Days", [])
                print(f"Days count: {len(days)}")
                if days:
                    print(f"First day keys: {list(days[0].keys())}")
                    print(f"First day sample: {json.dumps(days[0], ensure_ascii=False, indent=2)[:800]}")
                else:
                    print("No days in schedule (maybe no classes currently)")
            else:
                print(f"Schedule is list? {isinstance(sched_data, list)}")
        
        print("\n=== SUMMARY ===")
        print(f"Programs endpoint: /study/divisions/{{alias}}/programs/levels")
        print(f"Groups endpoint: /programs/{{program_id}}/groups  (returns dict with 'Groups' key)")
        print(f"Schedule endpoint: /groups/{{group_id}}/events")

if __name__ == "__main__":
    asyncio.run(main())
