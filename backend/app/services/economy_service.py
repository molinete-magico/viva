from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlmodel import Session, select

from app.models import Character, CharacterJob, Job, Schedule

MAX_SUMMARY = 60


def _overlaps(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    if end_a <= start_a:
        end_a = time(23, 59)
    if end_b <= start_b:
        end_b = time(23, 59)
    return start_a < end_b and start_b < end_a


def process_shifts_and_routines(session: Session, from_dt: datetime, until_dt: datetime) -> dict:
    if until_dt <= from_dt:
        return {"payments": [], "locations": 0}
    window_start = from_dt.time()
    window_end = until_dt.time()
    payments = []
    job_rows = session.exec(select(CharacterJob).where(CharacterJob.ended_at.is_(None))).all()
    characters = {c.id: c for c in session.exec(select(Character)).all()}
    for row in job_rows:
        character = characters.get(row.character_id)
        job = session.get(Job, row.job_id)
        if character is None or job is None or not character.is_npc:
            continue
        template = job.schedule_template or {}
        shifts = template.get("shifts") or []
        days = template.get("days") or list(range(7))
        if not shifts or job.salary_per_shift <= 0:
            continue
        day = from_dt.date()
        while day <= until_dt.date():
            if day.weekday() in days:
                for start_s, end_s in shifts:
                    try:
                        shift_start = time.fromisoformat(str(start_s))
                        shift_end = time.fromisoformat(str(end_s))
                    except ValueError:
                        continue
                    if _overlaps(shift_start, shift_end, window_start, window_end):
                        character.money = round((character.money or 0) + job.salary_per_shift, 2)
                        session.add(character)
                        payments.append(
                            {
                                "character_id": character.id,
                                "name": character.name,
                                "amount": job.salary_per_shift,
                                "job": job.title,
                                "day": day.isoformat(),
                            }
                        )
                        break
            day += timedelta(days=1)
    session.commit()

    schedules = session.exec(select(Schedule)).all()
    located = 0
    for schedule in schedules:
        character = characters.get(schedule.character_id)
        if character is None or not character.is_npc:
            continue
        if schedule.day_of_week is not None and schedule.day_of_week != until_dt.weekday():
            continue
        try:
            start_s = time.fromisoformat(schedule.start_time)
            end_s = time.fromisoformat(schedule.end_time)
        except ValueError:
            continue
        if start_s <= window_end <= end_s and schedule.location_id is not None:
            if character.current_location_id != schedule.location_id:
                character.current_location_id = schedule.location_id
                session.add(character)
                located += 1
    session.commit()
    return {"payments": payments, "locations": located}