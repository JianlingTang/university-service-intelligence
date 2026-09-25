#!/usr/bin/env python3
"""Generate and curate synthetic university service-operations data.

All records are artificial and are designed to demonstrate analytics patterns.
The script is deterministic: rerunning it with the same seed produces the same
data and validation results.
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20260815
RNG = np.random.default_rng(SEED)
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CURATED_DIR = ROOT / "data" / "curated"
DB_PATH = ROOT / "data" / "university_service_intelligence.db"
START_DATE = pd.Timestamp("2024-09-01")
END_DATE = pd.Timestamp("2026-08-15")
SYNTHETIC_LABEL = "Synthetic demonstration data — not actual University of Sydney results"


SERVICES = {
    1: {
        "service": "Student Administration",
        "owner": "Student Operations",
        "categories": [
            "Enrolment changes",
            "Timetable and class allocation",
            "Fees and payments",
            "Academic progression",
            "Documents and letters",
        ],
        "teams": [1, 2, 3, 4],
    },
    2: {
        "service": "IT Support",
        "owner": "ICT",
        "categories": [
            "Account access and login",
            "Learning platform",
            "Wi-Fi and network",
            "Device and software",
            "Multi-factor authentication",
        ],
        "teams": [5, 6, 7],
    },
    3: {
        "service": "Facilities",
        "owner": "Campus Infrastructure",
        "categories": [
            "Teaching room equipment",
            "HVAC and temperature",
            "Cleanliness",
            "Accessibility",
            "Security and lighting",
            "Study spaces",
        ],
        "teams": [8, 9, 10],
    },
}

TEAMS = {
    0: ("Unknown", 0),
    1: ("Student Operations", 1),
    2: ("Timetabling", 1),
    3: ("Fees and Scholarships", 1),
    4: ("Progression and Records", 1),
    5: ("IT Service Desk", 2),
    6: ("Learning Technology", 2),
    7: ("Network Services", 2),
    8: ("Facilities Helpdesk", 3),
    9: ("Campus Operations", 3),
    10: ("Accessibility Infrastructure", 3),
}

CAMPUSES = {
    0: "Unknown",
    1: "Camperdown/Darlington",
    2: "Westmead",
    3: "Camden",
}

COHORTS = {
    0: ("Unknown", "Unknown", "Unknown"),
    1: ("Undergraduate Domestic", "Student", "Domestic"),
    2: ("Undergraduate International", "Student", "International"),
    3: ("Postgraduate Coursework Domestic", "Student", "Domestic"),
    4: ("Postgraduate Coursework International", "Student", "International"),
    5: ("Higher Degree Research", "Student", "Mixed"),
    6: ("Academic Staff", "Academic Staff", "Not applicable"),
    7: ("Professional Staff", "Professional Staff", "Not applicable"),
}

CHANNELS = {
    1: "Portal",
    2: "Email",
    3: "Phone",
    4: "Chat",
    5: "Walk-in",
}

LIFECYCLE_STAGES = {
    0: "Unknown",
    1: "Pre-enrolment",
    2: "Commencing",
    3: "Continuing",
    4: "Completing",
    5: "Staff service",
}

SLA = {
    "P1": (4, 8),
    "P2": (8, 16),
    "P3": (16, 40),
    "P4": (24, 80),
}


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CURATED_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, date_format="%Y-%m-%d %H:%M:%S")


def academic_phase(date: pd.Timestamp) -> str:
    month, day = date.month, date.day
    if (month == 2 and day >= 15) or (month == 7 and day >= 15):
        return "Orientation"
    if month in (3, 4, 5, 8, 9, 10):
        return "Semester"
    if month in (6, 11):
        return "Examinations"
    return "Break"


def make_dimensions() -> dict[str, pd.DataFrame]:
    # Start on the Monday of the first week and run past the 12-week forecast so every weekly key resolves.
    dates = pd.date_range(START_DATE - pd.Timedelta(days=START_DATE.weekday()), END_DATE + pd.Timedelta(weeks=13), freq="D")
    dim_date = pd.DataFrame(
        {
            "date_key": dates.strftime("%Y%m%d").astype(int),
            "date": dates,
            "month_start": dates.to_period("M").to_timestamp(),
            "year": dates.year,
            "month_number": dates.month,
            "month_name": dates.strftime("%b"),
            "year_month": dates.strftime("%Y-%m"),
            "quarter": "Q" + dates.quarter.astype(str),
            "weekday": dates.strftime("%a"),
            "is_weekend": (dates.weekday >= 5).astype(int),
            "is_working_day": (dates.weekday < 5).astype(int),
            "academic_phase": [academic_phase(d) for d in dates],
            "is_partial_period": ((dates.year == END_DATE.year) & (dates.month == END_DATE.month)).astype(int),
            "is_future": (dates > END_DATE).astype(int),
        }
    )

    dim_service = pd.DataFrame(
        [
            {
                "service_key": key,
                "service_name": value["service"],
                "executive_owner": value["owner"],
                "is_student_facing": 1,
            }
            for key, value in SERVICES.items()
        ]
    )
    dim_team = pd.DataFrame(
        [
            {"team_key": key, "team_name": name, "service_key": service_key}
            for key, (name, service_key) in TEAMS.items()
        ]
    )
    dim_campus = pd.DataFrame(
        [{"campus_key": key, "campus_name": name} for key, name in CAMPUSES.items()]
    )
    dim_cohort = pd.DataFrame(
        [
            {
                "cohort_key": key,
                "cohort_name": values[0],
                "requester_type": values[1],
                "domestic_international": values[2],
            }
            for key, values in COHORTS.items()
        ]
    )
    dim_channel = pd.DataFrame(
        [{"channel_key": key, "channel_name": name} for key, name in CHANNELS.items()]
    )
    dim_sla = pd.DataFrame(
        [
            {
                "priority": priority,
                "first_response_target_business_hours": targets[0],
                "resolution_target_business_hours": targets[1],
                "sla_description": f"{targets[0]}h response / {targets[1]}h resolution",
            }
            for priority, targets in SLA.items()
        ]
    )
    dim_lifecycle_stage = pd.DataFrame(
        [
            {"lifecycle_stage_key": key, "lifecycle_stage": name}
            for key, name in LIFECYCLE_STAGES.items()
        ]
    )
    return {
        "dim_date": dim_date,
        "dim_service": dim_service,
        "dim_team": dim_team,
        "dim_campus": dim_campus,
        "dim_cohort": dim_cohort,
        "dim_channel": dim_channel,
        "dim_sla": dim_sla,
        "dim_lifecycle_stage": dim_lifecycle_stage,
    }


def sample_submission_dates(n: int) -> pd.Series:
    days = pd.date_range(START_DATE, END_DATE, freq="D")
    weights = np.ones(len(days), dtype=float)
    peak = np.isin(days.month, [2, 3, 7, 8])
    weights[peak] *= 1.65
    weights[days.weekday >= 5] *= 0.45
    weights /= weights.sum()
    chosen = RNG.choice(days.to_numpy(), size=n, replace=True, p=weights)
    hours = RNG.choice(np.arange(8, 21), size=n, p=np.array([4, 6, 8, 9, 10, 11, 11, 10, 9, 8, 6, 5, 3]) / 100)
    minutes = RNG.integers(0, 60, size=n)
    return pd.Series(pd.to_datetime(chosen) + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m"))


def sample_service(n: int) -> np.ndarray:
    return RNG.choice([1, 2, 3], size=n, p=[0.49, 0.31, 0.20])


def sample_cohort(service_key: int) -> int:
    if service_key == 1:
        return int(RNG.choice([1, 2, 3, 4, 5], p=[0.31, 0.20, 0.16, 0.25, 0.08]))
    if service_key == 2:
        return int(RNG.choice([1, 2, 3, 4, 5, 6, 7], p=[0.25, 0.14, 0.09, 0.17, 0.06, 0.12, 0.17]))
    return int(RNG.choice([1, 2, 3, 4, 5, 6, 7], p=[0.23, 0.14, 0.09, 0.16, 0.05, 0.14, 0.19]))


def team_for_category(service_key: int, category: str) -> int:
    if service_key == 1:
        if category == "Timetable and class allocation":
            return 2
        if category == "Fees and payments":
            return 3
        if category in ("Academic progression", "Documents and letters"):
            return 4
        return 1
    if service_key == 2:
        if category == "Learning platform":
            return 6
        if category == "Wi-Fi and network":
            return 7
        return 5
    if category == "Accessibility":
        return 10
    if category in ("HVAC and temperature", "Cleanliness", "Security and lighting", "Study spaces"):
        return 9
    return 8


def lifecycle_stage_for_case(cohort_key: int, category: str) -> int:
    if cohort_key in (6, 7):
        return 5
    if category in ("Enrolment changes", "Account access and login", "Multi-factor authentication"):
        return int(RNG.choice([1, 2, 3], p=[0.18, 0.42, 0.40]))
    if category in ("Documents and letters", "Academic progression"):
        return int(RNG.choice([3, 4], p=[0.38, 0.62]))
    return int(RNG.choice([2, 3, 4], p=[0.18, 0.68, 0.14]))


def generate_cases(n: int = 18_000) -> pd.DataFrame:
    submissions = sample_submission_dates(n)
    service_keys = sample_service(n)
    rows: list[dict] = []

    for idx in range(n):
        case_id = f"CASE-{idx + 1:06d}"
        submitted = submissions.iloc[idx]
        service_key = int(service_keys[idx])
        service = SERVICES[service_key]
        category_weights = np.ones(len(service["categories"]))
        if service_key == 1 and submitted.month in (2, 3, 7, 8):
            category_weights[:2] = [1.8, 2.3]
        if service_key == 2:
            category_weights[0] = 2.5
        if service_key == 3:
            category_weights[[1, 5]] = [1.6, 1.5]
        category_weights /= category_weights.sum()
        category = str(RNG.choice(service["categories"], p=category_weights))
        cohort_key = sample_cohort(service_key)
        requester_type = COHORTS[cohort_key][1]
        lifecycle_stage_key = lifecycle_stage_for_case(cohort_key, category)
        campus_key = int(RNG.choice([1, 2, 3], p=[0.73, 0.18, 0.09]))
        channel_key = int(RNG.choice([1, 2, 3, 4, 5], p=[0.43, 0.24, 0.12, 0.15, 0.06]))
        case_type = str(RNG.choice(["Service Request", "Enquiry", "Complaint", "Idea"], p=[0.47, 0.31, 0.18, 0.04]))
        priority = str(RNG.choice(["P1", "P2", "P3", "P4"], p=[0.025, 0.13, 0.62, 0.225]))
        first_target, resolution_target = SLA[priority]

        base_first = max(0.5, float(RNG.lognormal(mean=1.55, sigma=0.65)))
        base_resolution = max(base_first + 1, float(RNG.lognormal(mean=3.15, sigma=0.7)))
        triage_hours = max(0.25, base_first * float(RNG.uniform(0.35, 0.75)))
        assignment_hours = max(0.5, base_resolution * float(RNG.uniform(0.10, 0.28)))

        peak_admin = service_key == 1 and submitted.month in (2, 3, 7, 8)
        admin_bottleneck = service_key == 1 and category in ("Enrolment changes", "Timetable and class allocation")
        it_login = service_key == 2 and category in ("Account access and login", "Multi-factor authentication")
        facilities_hotspot = (
            service_key == 3
            and campus_key == 1
            and category in ("HVAC and temperature", "Study spaces")
        )

        if peak_admin:
            base_first *= 1.55
            base_resolution *= 1.55
        if admin_bottleneck:
            assignment_hours *= 2.4
            base_resolution *= 1.30
        if service_key == 2 and category == "Learning platform":
            base_resolution *= 1.25
        if facilities_hotspot:
            base_first *= 1.7
            base_resolution *= 2.0
            assignment_hours *= 1.4
        if cohort_key == 4:
            base_resolution *= 1.18
        if admin_bottleneck and submitted >= pd.Timestamp("2026-02-01"):
            assignment_hours *= 0.62
            base_resolution *= 0.78

        first_response_hours = round(base_first, 2)
        resolution_hours = round(max(base_resolution, first_response_hours + assignment_hours), 2)
        age_days = max(0, (END_DATE - submitted.normalize()).days)

        final_draw = RNG.random()
        if age_days < 10 and final_draw < 0.42:
            status = str(RNG.choice(["Submitted", "Triaged", "Assigned", "In Progress"], p=[0.08, 0.20, 0.32, 0.40]))
        elif final_draw < 0.035:
            status = "Merged Duplicate"
        elif final_draw < 0.055:
            status = "Withdrawn"
        elif final_draw < 0.070:
            status = "Cancelled"
        else:
            status = "Resolved"

        eligible = status == "Resolved"
        calendar_resolution_hours = resolution_hours * 1.55 + float(RNG.uniform(0, 10))
        closed = submitted + pd.to_timedelta(calendar_resolution_hours, unit="h") if status in ("Resolved", "Merged Duplicate", "Withdrawn", "Cancelled") else pd.NaT
        if pd.notna(closed) and closed > END_DATE + pd.Timedelta(days=1):
            closed = pd.NaT
            status = "In Progress"
            eligible = False

        handoff_prob = 0.16
        if admin_bottleneck:
            handoff_prob += 0.20
        if facilities_hotspot:
            handoff_prob += 0.10
        if admin_bottleneck and submitted >= pd.Timestamp("2026-02-01"):
            handoff_prob -= 0.12
        handoff_count = int(RNG.binomial(3, min(max(handoff_prob, 0.02), 0.75)))
        reopen_prob = 0.045 + (0.06 if facilities_hotspot else 0) + (0.025 if cohort_key == 4 else 0)
        reopened_flag = int(eligible and RNG.random() < reopen_prob)
        sla_breached = int(eligible and resolution_hours > resolution_target)
        first_response_breached = int(first_response_hours > first_target)
        complexity_weight = round({"P1": 2.2, "P2": 1.6, "P3": 1.0, "P4": 0.7}[priority] * float(RNG.uniform(0.85, 1.2)), 2)
        handle_hours = round(complexity_weight * float(RNG.uniform(0.45, 1.3)) + handoff_count * 0.35 + reopened_flag * 0.8, 2)
        assigned_team_key = team_for_category(service_key, category)

        summary_templates = {
            "Student Administration": "Request for help with {category} and clarification of the next step.",
            "IT Support": "Unable to complete a university task because of {category}.",
            "Facilities": "Service issue reported for {category} at the selected campus.",
        }
        case_summary = summary_templates[service["service"]].format(category=category.lower())

        rows.append(
            {
                "case_id": case_id,
                "submitted_datetime": submitted,
                "submitted_date_key": int(submitted.strftime("%Y%m%d")),
                "closed_datetime": closed,
                "service_key": service_key,
                "team_key": assigned_team_key,
                "campus_key": campus_key,
                "cohort_key": cohort_key,
                "lifecycle_stage_key": lifecycle_stage_key,
                "channel_key": channel_key,
                "requester_type": requester_type,
                "case_type": case_type,
                "category": category,
                "priority": priority,
                "current_status": status,
                "first_response_business_hours": first_response_hours,
                "triage_business_hours": round(triage_hours, 2),
                "assignment_business_hours": round(assignment_hours, 2),
                "resolution_business_hours": resolution_hours if eligible else np.nan,
                "first_response_sla_breached": first_response_breached,
                "resolution_sla_breached": sla_breached,
                "handoff_count": handoff_count,
                "reopened_flag": reopened_flag,
                "repeat_contact_14d": 0,
                "first_contact_resolution_flag": 0,
                "complexity_weight": complexity_weight,
                "staff_handle_hours": handle_hours,
                "estimated_cost_aud": round(handle_hours * 62.0 + (18 if service_key == 3 else 0), 2),
                "case_summary": case_summary,
                "synthetic_label": SYNTHETIC_LABEL,
                "ai_theme": "",
                "ai_summary": "",
                "ai_recommended_owner": "",
                "ai_confidence": np.nan,
                "ai_review_status": "Not run",
                "source_extract_ts": pd.Timestamp("2026-08-15 12:00:00"),
            }
        )

    return pd.DataFrame(rows)


def generate_events(cases: pd.DataFrame, target_count: int = 70_000) -> pd.DataFrame:
    events: list[dict] = []
    event_id = 1
    for row in cases.itertuples(index=False):
        submitted = pd.Timestamp(row.submitted_datetime)
        closed = pd.Timestamp(row.closed_datetime) if pd.notna(row.closed_datetime) else None
        total_calendar_hours = max(2.0, (closed - submitted).total_seconds() / 3600) if closed is not None else max(12.0, row.first_response_business_hours * 3)

        stages = [("Submitted", 0.0, 0)]
        if RNG.random() < 0.95:
            stages.append(("Triaged", min(total_calendar_hours * 0.18, row.triage_business_hours * 1.6), row.team_key))
        if row.current_status not in ("Submitted", "Withdrawn") and RNG.random() < 0.92:
            stages.append(("Assigned", min(total_calendar_hours * 0.58, (row.triage_business_hours + row.assignment_business_hours) * 1.6), row.team_key))
        if row.current_status in ("In Progress", "Resolved") and RNG.random() < 0.22:
            stages.append(("In Progress", total_calendar_hours * 0.72, row.team_key))
        if closed is not None:
            stages.append((row.current_status, total_calendar_hours, row.team_key))

        stages = sorted(stages, key=lambda x: x[1])
        previous = "New"
        for stage, hours_after, team_key in stages:
            events.append(
                {
                    "event_id": f"EVT-{event_id:07d}",
                    "case_id": row.case_id,
                    "event_datetime": submitted + pd.to_timedelta(hours_after, unit="h"),
                    "from_status": previous,
                    "to_status": stage,
                    "team_key": team_key,
                    "event_type": "Status Change",
                    "business_hours_since_previous": round(max(0, hours_after) / 1.55, 2),
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
            event_id += 1
            previous = stage

    if len(events) < target_count:
        eligible_cases = cases[cases["current_status"].isin(["Assigned", "In Progress", "Resolved"])].sample(
            target_count - len(events), replace=True, random_state=SEED
        )
        for row in eligible_cases.itertuples(index=False):
            submitted = pd.Timestamp(row.submitted_datetime)
            max_hours = max(4, (END_DATE - submitted).total_seconds() / 3600)
            hours_after = float(RNG.uniform(2, min(max_hours, 240)))
            events.append(
                {
                    "event_id": f"EVT-{event_id:07d}",
                    "case_id": row.case_id,
                    "event_datetime": submitted + pd.to_timedelta(hours_after, unit="h"),
                    "from_status": row.current_status,
                    "to_status": row.current_status,
                    "team_key": row.team_key,
                    "event_type": "Progress Update",
                    "business_hours_since_previous": round(hours_after / 1.55, 2),
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
            event_id += 1
    elif len(events) > target_count:
        core = [event for event in events if event["to_status"] in ("Submitted", "Resolved", "Merged Duplicate", "Withdrawn", "Cancelled")]
        optional = [event for event in events if event not in core]
        keep_optional = target_count - len(core)
        optional = list(RNG.choice(optional, size=keep_optional, replace=False)) if keep_optional > 0 else []
        events = core + optional
        events.sort(key=lambda event: event["event_id"])
    return pd.DataFrame(events[:target_count])


def generate_interactions(cases: pd.DataFrame, target_count: int = 35_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    counts = np.ones(len(cases), dtype=int)
    for i, row in enumerate(cases.itertuples(index=False)):
        prob = 0.18
        if row.service_key == 2 and row.category in ("Account access and login", "Multi-factor authentication"):
            prob = 0.34 if pd.Timestamp(row.submitted_datetime) < pd.Timestamp("2025-10-01") else 0.19
        if row.service_key == 1 and row.category in ("Enrolment changes", "Timetable and class allocation"):
            prob += 0.12
        if row.cohort_key == 4:
            prob += 0.08
        if row.handoff_count > 0:
            prob += 0.08
        counts[i] += int(RNG.binomial(3, min(prob, 0.75)))

    while counts.sum() < target_count:
        counts[int(RNG.integers(0, len(counts)))] += 1
    while counts.sum() > target_count:
        candidates = np.where(counts > 1)[0]
        counts[int(RNG.choice(candidates))] -= 1

    interactions: list[dict] = []
    repeat_flags = np.zeros(len(cases), dtype=int)
    first_contact_flags = np.zeros(len(cases), dtype=int)
    interaction_id = 1
    for i, row in enumerate(cases.itertuples(index=False)):
        submitted = pd.Timestamp(row.submitted_datetime)
        duration_days = max(1.0, ((pd.Timestamp(row.closed_datetime) if pd.notna(row.closed_datetime) else END_DATE) - submitted).total_seconds() / 86400)
        timed_interactions: list[tuple[pd.Timestamp, int]] = [(submitted, 1)]
        for j in range(1, counts[i]):
            if j == 1:
                day_offset = float(RNG.uniform(0.2, min(14, duration_days)))
            else:
                day_offset = float(RNG.uniform(0.3, min(max(0.4, duration_days), 28)))
            follow_up_time = submitted + pd.to_timedelta(day_offset, unit="D")
            requester_prob = 0.34
            if row.service_key == 2 and row.category in ("Account access and login", "Multi-factor authentication"):
                requester_prob = 0.54 if submitted < pd.Timestamp("2025-10-01") else 0.30
            if row.cohort_key == 4:
                requester_prob += 0.08
            timed_interactions.append((follow_up_time, int(RNG.random() < requester_prob)))
        timed_interactions.sort(key=lambda item: item[0])
        repeat_flags[i] = int(
            any(
                requester_initiated == 1 and (event_time - submitted).total_seconds() <= 14 * 86400
                for event_time, requester_initiated in timed_interactions[1:]
            )
        )
        first_contact_flags[i] = int(row.current_status == "Resolved" and repeat_flags[i] == 0 and row.handoff_count == 0 and row.reopened_flag == 0)

        for j, (event_time, requester_initiated) in enumerate(timed_interactions):
            interactions.append(
                {
                    "interaction_id": f"INT-{interaction_id:07d}",
                    "case_id": row.case_id,
                    "interaction_datetime": event_time,
                    "channel_key": row.channel_key if j == 0 else int(RNG.choice([1, 2, 3, 4], p=[0.34, 0.30, 0.18, 0.18])),
                    "direction": "Inbound" if requester_initiated else "Outbound",
                    "requester_initiated": requester_initiated,
                    "interaction_sequence": j + 1,
                    "handle_minutes": int(max(3, RNG.normal(16 + row.complexity_weight * 4, 6))),
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
            interaction_id += 1

    updated = cases.copy()
    updated["repeat_contact_14d"] = repeat_flags
    updated["first_contact_resolution_flag"] = first_contact_flags
    return pd.DataFrame(interactions), updated


def generate_work_orders(cases: pd.DataFrame, n: int = 1_500) -> pd.DataFrame:
    facilities = cases[cases["service_key"] == 3].sample(n=n, replace=False, random_state=SEED)
    rows = []
    vendors = ["CampusWorks Services", "Metro Building Care", "Learning Spaces Technical"]
    for idx, row in enumerate(facilities.itertuples(index=False), start=1):
        hotspot = row.campus_key == 1 and row.category in ("HVAC and temperature", "Study spaces")
        after_action = pd.Timestamp(row.submitted_datetime) >= pd.Timestamp("2026-04-01")
        on_time_prob = 0.72 if hotspot else 0.90
        rework_prob = 0.19 if hotspot else 0.08
        if hotspot and after_action:
            on_time_prob = 0.87
            rework_prob = 0.10
        response_hours = max(0.5, float(RNG.lognormal(2.1 if hotspot else 1.5, 0.55)))
        completion_hours = max(response_hours + 1, float(RNG.lognormal(3.6 if hotspot else 3.0, 0.6)))
        on_time = int(RNG.random() < on_time_prob)
        rework = int(RNG.random() < rework_prob)
        rows.append(
            {
                "work_order_id": f"WO-{idx:05d}",
                "case_id": row.case_id,
                "created_datetime": row.submitted_datetime,
                "completed_datetime": pd.Timestamp(row.submitted_datetime) + pd.to_timedelta(completion_hours * 1.5, unit="h"),
                "campus_key": row.campus_key,
                "team_key": row.team_key,
                "category": row.category,
                "contractor_name": str(RNG.choice(vendors)),
                "response_business_hours": round(response_hours, 2),
                "completion_business_hours": round(completion_hours, 2),
                "on_time_flag": on_time,
                "rework_flag": rework,
                "contractor_cost_aud": round(float(RNG.lognormal(5.7, 0.65)), 2),
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )
    return pd.DataFrame(rows)


def generate_feedback(cases: pd.DataFrame, work_orders: pd.DataFrame, n: int = 6_000) -> pd.DataFrame:
    case_feedback = cases[cases["current_status"] == "Resolved"].sample(n=5_400, random_state=SEED)
    rows: list[dict] = []
    feedback_id = 1
    themes = ["Clarity", "Waiting time", "Ownership", "Ease of use", "Communication", "Outcome quality"]
    for row in case_feedback.itertuples(index=False):
        score = 4.25
        score -= min(row.resolution_business_hours / 100, 1.2)
        score -= row.handoff_count * 0.22
        score -= row.reopened_flag * 0.55
        score -= 0.25 if row.cohort_key == 4 else 0
        score -= 0.35 if row.repeat_contact_14d else 0
        csat = int(np.clip(round(RNG.normal(score, 0.75)), 1, 5))
        ces = int(np.clip(round(RNG.normal(score - 0.15, 0.8)), 1, 5))
        theme = str(RNG.choice(themes, p=[0.18, 0.26, 0.16, 0.15, 0.13, 0.12]))
        rows.append(
            {
                "feedback_id": f"FDB-{feedback_id:06d}",
                "feedback_date": pd.Timestamp(row.closed_datetime).normalize(),
                "related_case_id": row.case_id,
                "related_work_order_id": "",
                "respondent_type": row.requester_type,
                "service_key": row.service_key,
                "campus_key": row.campus_key,
                "cohort_key": row.cohort_key,
                "feedback_type": "Post-case survey",
                "csat_score": csat,
                "ces_score": ces,
                "feedback_theme": theme,
                "comment_text": f"Synthetic feedback concerning {theme.lower()} for {row.category.lower()}.",
                "response_valid": 1,
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )
        feedback_id += 1

    staff_cases = cases.sample(n=400, random_state=SEED + 1)
    for row in staff_cases.itertuples(index=False):
        csat = int(np.clip(round(RNG.normal(3.45 - 0.12 * row.handoff_count, 0.8)), 1, 5))
        rows.append(
            {
                "feedback_id": f"FDB-{feedback_id:06d}",
                "feedback_date": pd.Timestamp(row.submitted_datetime).normalize(),
                "related_case_id": "",
                "related_work_order_id": "",
                "respondent_type": "Service Employee",
                "service_key": row.service_key,
                "campus_key": row.campus_key,
                "cohort_key": 0,
                "feedback_type": "Employee pulse",
                "csat_score": csat,
                "ces_score": int(np.clip(csat + RNG.choice([-1, 0, 1]), 1, 5)),
                "feedback_theme": str(RNG.choice(["Workload", "Tooling", "Ownership", "Process clarity"])),
                "comment_text": "Synthetic employee pulse response about operational delivery.",
                "response_valid": 1,
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )
        feedback_id += 1

    contractor_sample = work_orders.sample(n=200, random_state=SEED + 2)
    for row in contractor_sample.itertuples(index=False):
        score = 4 - row.rework_flag - (1 - row.on_time_flag)
        rows.append(
            {
                "feedback_id": f"FDB-{feedback_id:06d}",
                "feedback_date": pd.Timestamp(row.completed_datetime).normalize(),
                "related_case_id": row.case_id,
                "related_work_order_id": row.work_order_id,
                "respondent_type": "Contractor",
                "service_key": 3,
                "campus_key": row.campus_key,
                "cohort_key": 0,
                "feedback_type": "Contractor close-out",
                "csat_score": int(np.clip(score, 1, 5)),
                "ces_score": int(np.clip(score + RNG.choice([-1, 0, 1]), 1, 5)),
                "feedback_theme": str(RNG.choice(["Site access", "Job clarity", "Approval delay", "Parts availability"])),
                "comment_text": "Synthetic contractor close-out feedback.",
                "response_valid": 1,
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )
        feedback_id += 1
    assert len(rows) == n
    return pd.DataFrame(rows)


def generate_capacity(cases: pd.DataFrame) -> pd.DataFrame:
    weeks = pd.date_range(START_DATE - pd.to_timedelta(START_DATE.weekday(), unit="D"), END_DATE, freq="W-MON")
    case_week = cases.assign(week_start=pd.to_datetime(cases["submitted_datetime"]).dt.to_period("W-SUN").dt.start_time)
    demand = case_week.groupby(["week_start", "team_key"]).agg(
        cases_received=("case_id", "nunique"),
        required_handle_hours=("staff_handle_hours", "sum"),
    ).reset_index()
    rows = []
    for week in weeks:
        for team_key, (_, service_key) in TEAMS.items():
            if team_key == 0:
                continue
            match = demand[(demand["week_start"] == week) & (demand["team_key"] == team_key)]
            case_count = int(match["cases_received"].iloc[0]) if not match.empty else 0
            required = float(match["required_handle_hours"].iloc[0]) if not match.empty else 0.0
            base_fte = {1: 7.5, 2: 6.0, 3: 4.5}[service_key] / len(SERVICES[service_key]["teams"])
            peak = week.month in (2, 3, 7, 8)
            absence = float(np.clip(RNG.normal(0.09 if peak else 0.06, 0.025), 0.01, 0.18))
            fte = max(0.8, base_fte * float(RNG.uniform(0.9, 1.12)))
            available = fte * 38 * (1 - absence) * 0.72
            if service_key == 1 and peak:
                available *= 0.90
            if service_key == 1 and week >= pd.Timestamp("2026-02-01"):
                available *= 1.06
            forecast = required * float(RNG.uniform(0.91, 1.08))
            rows.append(
                {
                    "week_start": week,
                    "week_date_key": int(week.strftime("%Y%m%d")),
                    "team_key": team_key,
                    "service_key": service_key,
                    "fte_available": round(fte, 2),
                    "absence_rate": round(absence, 4),
                    "staffed_hours": round(available, 2),
                    "cases_received": case_count,
                    "required_handle_hours": round(required, 2),
                    "forecast_handle_hours": round(forecast, 2),
                    "capacity_gap_hours": round(required - available, 2),
                    "capacity_gap_pct": round((required - available) / available, 4) if available else np.nan,
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
    return pd.DataFrame(rows)


def generate_digital(cases: pd.DataFrame) -> pd.DataFrame:
    daily_cases = cases[cases["service_key"].isin([1, 2])].assign(
        date=pd.to_datetime(cases[cases["service_key"].isin([1, 2])]["submitted_datetime"]).dt.normalize()
    ).groupby(["date", "service_key"]).size().rename("case_count").reset_index()
    rows = []
    for date in pd.date_range(START_DATE, END_DATE, freq="D"):
        for service_key in [1, 2]:
            match = daily_cases[(daily_cases["date"] == date) & (daily_cases["service_key"] == service_key)]
            case_count = int(match["case_count"].iloc[0]) if not match.empty else 0
            sessions = max(20, int(case_count * RNG.uniform(4.0, 7.0) + RNG.normal(85, 18)))
            if service_key == 2:
                completion_rate = 0.56 if date < pd.Timestamp("2025-10-01") else 0.72
            else:
                completion_rate = 0.68 if date.month not in (2, 3, 7, 8) else 0.58
            completion_rate = float(np.clip(RNG.normal(completion_rate, 0.045), 0.38, 0.88))
            completions = int(round(sessions * completion_rate))
            abandonments = sessions - completions
            deflected = int(completions * RNG.uniform(0.38, 0.62))
            rows.append(
                {
                    "date": date,
                    "date_key": int(date.strftime("%Y%m%d")),
                    "service_key": service_key,
                    "self_service_sessions": sessions,
                    "successful_completions": completions,
                    "abandonments": abandonments,
                    "estimated_cases_deflected": deflected,
                    "completion_rate": round(completion_rate, 4),
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
    return pd.DataFrame(rows)


def generate_population() -> pd.DataFrame:
    months = pd.date_range(START_DATE.to_period("M").start_time, END_DATE.to_period("M").start_time, freq="MS")
    base = {1: 25_000, 2: 15_000, 3: 8_000, 4: 12_000, 5: 5_000, 6: 4_200, 7: 7_500}
    campus_share = {1: 0.78, 2: 0.15, 3: 0.07}
    rows = []
    for month in months:
        for cohort_key, base_count in base.items():
            season = 1.0 + (0.03 if month.month in (3, 8) else -0.015 if month.month in (1, 12) else 0)
            growth = 1 + 0.006 * ((month.year - START_DATE.year) * 12 + month.month - START_DATE.month)
            stage_shares = {5: 1.0} if cohort_key in (6, 7) else {1: 0.06, 2: 0.22, 3: 0.60, 4: 0.12}
            for campus_key, share in campus_share.items():
                campus_users = int(base_count * share * season * growth * RNG.uniform(0.985, 1.015))
                for lifecycle_stage_key, stage_share in stage_shares.items():
                    rows.append(
                        {
                            "month_start": month,
                            "month_date_key": int(month.strftime("%Y%m%d")),
                            "campus_key": campus_key,
                            "cohort_key": cohort_key,
                            "lifecycle_stage_key": lifecycle_stage_key,
                            "active_users": int(campus_users * stage_share),
                            "synthetic_label": SYNTHETIC_LABEL,
                        }
                    )
    return pd.DataFrame(rows)


def generate_demand_forecast(cases: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a transparent seasonal regression and 12-week forward forecast."""
    case_week = cases.assign(
        week_start=pd.to_datetime(cases["submitted_datetime"]).dt.to_period("W-SUN").dt.start_time
    )
    weekly = (
        case_week.groupby(["week_start", "service_key"])
        .agg(actual_cases=("case_id", "nunique"), actual_handle_hours=("staff_handle_hours", "sum"))
        .reset_index()
    )
    all_weeks = pd.date_range(weekly.week_start.min(), weekly.week_start.max(), freq="W-MON")
    future_weeks = pd.date_range(all_weeks.max() + pd.Timedelta(days=7), periods=12, freq="W-MON")
    output_rows: list[dict] = []
    evaluation_rows: list[dict] = []

    def feature_matrix(weeks: pd.Series | pd.DatetimeIndex, origin: pd.Timestamp) -> np.ndarray:
        week_index = np.array([(pd.Timestamp(w) - origin).days / 7 for w in weeks], dtype=float)
        months = np.array([pd.Timestamp(w).month for w in weeks])
        peak = np.isin(months, [2, 3, 7, 8]).astype(float)
        return np.column_stack(
            [
                np.ones(len(week_index)),
                week_index,
                np.sin(2 * np.pi * week_index / 52.18),
                np.cos(2 * np.pi * week_index / 52.18),
                peak,
            ]
        )

    for service_key in SERVICES:
        service_actual = weekly[weekly.service_key == service_key].set_index("week_start").reindex(all_weeks, fill_value=0)
        y = service_actual["actual_cases"].to_numpy(dtype=float)
        origin = all_weeks.min()
        holdout = 12
        train_weeks = all_weeks[:-holdout]
        test_weeks = all_weeks[-holdout:]
        x_train = feature_matrix(train_weeks, origin)
        beta = np.linalg.lstsq(x_train, y[:-holdout], rcond=None)[0]
        train_residuals = y[:-holdout] - x_train @ beta
        residual_sd = float(np.std(train_residuals, ddof=x_train.shape[1]))
        x_test = feature_matrix(test_weeks, origin)
        test_pred = np.maximum(0, x_test @ beta)
        test_actual = y[-holdout:]
        error = test_actual - test_pred
        wape = float(np.abs(error).sum() / max(test_actual.sum(), 1))
        evaluation_rows.append(
            {
                "model_version": "seasonal_linear_v1",
                "service_key": service_key,
                "training_end_week": train_weeks.max(),
                "holdout_weeks": holdout,
                "mae_cases": round(float(np.mean(np.abs(error))), 2),
                "rmse_cases": round(float(np.sqrt(np.mean(error**2))), 2),
                "wape": round(wape, 4),
                "forecast_bias": round(float(error.sum() / max(test_actual.sum(), 1)), 4),
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )

        x_full = feature_matrix(all_weeks, origin)
        beta_full = np.linalg.lstsq(x_full, y, rcond=None)[0]
        avg_hours_per_case = float(
            weekly[weekly.service_key == service_key].actual_handle_hours.sum()
            / max(weekly[weekly.service_key == service_key].actual_cases.sum(), 1)
        )
        typical_capacity = float(
            cases[cases.service_key == service_key].staff_handle_hours.sum() / max(len(all_weeks), 1) * 1.05
        )
        combined_weeks = all_weeks.append(future_weeks)
        predictions = np.maximum(0, feature_matrix(combined_weeks, origin) @ beta_full)
        actual_lookup = dict(zip(all_weeks, y))
        for week, prediction in zip(combined_weeks, predictions):
            actual = actual_lookup.get(week, np.nan)
            predicted_hours = prediction * avg_hours_per_case
            output_rows.append(
                {
                    "week_start": week,
                    "week_date_key": int(week.strftime("%Y%m%d")),
                    "service_key": service_key,
                    "actual_cases": actual,
                    "predicted_cases": round(float(prediction), 2),
                    "lower_95_cases": round(float(max(0, prediction - 1.96 * residual_sd)), 2),
                    "upper_95_cases": round(float(prediction + 1.96 * residual_sd), 2),
                    "predicted_handle_hours": round(float(predicted_hours), 2),
                    "typical_capacity_hours": round(typical_capacity, 2),
                    "predicted_capacity_gap_hours": round(float(predicted_hours - typical_capacity), 2),
                    "record_type": "Forecast" if week > all_weeks.max() else "Historical fit",
                    "model_version": "seasonal_linear_v1",
                    "forecast_generated_date": END_DATE,
                    "synthetic_label": SYNTHETIC_LABEL,
                }
            )
    return pd.DataFrame(output_rows), pd.DataFrame(evaluation_rows)


def pct(series: pd.Series) -> float:
    return float(series.mean()) if len(series) else 0.0


def create_actions(
    cases: pd.DataFrame,
    feedback: pd.DataFrame,
    capacity: pd.DataFrame,
    work_orders: pd.DataFrame,
    digital: pd.DataFrame,
) -> pd.DataFrame:
    resolved = cases[cases["current_status"] == "Resolved"].copy()
    joined_feedback = feedback[feedback["feedback_type"] == "Post-case survey"].merge(
        cases[["case_id", "service_key", "category", "campus_key", "cohort_key"]],
        left_on="related_case_id",
        right_on="case_id",
        suffixes=("", "_case"),
    )

    slices = {
        "admin": resolved[(resolved.service_key == 1) & resolved.category.isin(["Enrolment changes", "Timetable and class allocation"])],
        "it": resolved[(resolved.service_key == 2) & resolved.category.isin(["Account access and login", "Multi-factor authentication"])],
        "fac": resolved[(resolved.service_key == 3) & (resolved.campus_key == 1) & resolved.category.isin(["HVAC and temperature", "Study spaces"])],
        "pg_int": resolved[resolved.cohort_key == 4],
        "learning": resolved[(resolved.service_key == 2) & (resolved.category == "Learning platform")],
        "fees": resolved[(resolved.service_key == 1) & (resolved.category == "Fees and payments")],
    }
    actions = []

    def add_action(
        action_id: str,
        service_key: int,
        campus_key: int,
        cohort_key: int,
        issue: str,
        evidence_1_name: str,
        evidence_1_value: float,
        evidence_2_name: str,
        evidence_2_value: float,
        sample_size: int,
        recommended_action: str,
        owner_team_key: int,
        success_measure: str,
        baseline: float,
        target: float,
        actual: float | None,
        unit: str,
        status: str,
        priority: str,
        review_date: str,
        avoidable_hours: float,
        negative_experience: float,
        users_affected: int,
        sla_breach: float,
    ) -> None:
        actions.append(
            {
                "action_id": action_id,
                "insight_date": END_DATE,
                "service_key": service_key,
                "campus_key": campus_key,
                "cohort_key": cohort_key,
                "issue": issue,
                "evidence_1_name": evidence_1_name,
                "evidence_1_value": round(evidence_1_value, 4),
                "evidence_2_name": evidence_2_name,
                "evidence_2_value": round(evidence_2_value, 4),
                "sample_size": sample_size,
                "recommended_action": recommended_action,
                "suggested_owner_team_key": owner_team_key,
                "success_measure": success_measure,
                "baseline_value": round(baseline, 4),
                "target_value": round(target, 4),
                "actual_value": round(actual, 4) if actual is not None else np.nan,
                "unit": unit,
                "action_status": status,
                "priority": priority,
                "next_review_date": pd.Timestamp(review_date),
                "estimated_avoidable_staff_hours": round(avoidable_hours, 1),
                "negative_experience_rate": round(negative_experience, 4),
                "users_affected": users_affected,
                "sla_breach_rate": round(sla_breach, 4),
                "synthetic_label": SYNTHETIC_LABEL,
            }
        )

    admin = slices["admin"]
    admin_neg = joined_feedback[(joined_feedback.service_key_case == 1) & joined_feedback.category.isin(["Enrolment changes", "Timetable and class allocation"])]["csat_score"].lt(4).mean()
    add_action("ACT-001", 1, 0, 0, "Assignment delays in enrolment and timetable cases", "Handoff rate", pct(admin.handoff_count.gt(0)), "SLA breach rate", pct(admin.resolution_sla_breached), len(admin), "Introduce rules-based routing and a seven-business-hour assignment threshold.", 1, "Median assignment business hours", float(admin.assignment_business_hours.median()), float(admin.assignment_business_hours.median() * 0.7), float(admin[admin.submitted_datetime >= "2026-02-01"].assignment_business_hours.median()), "business hours", "In progress", "High", "2026-09-30", float(admin.handoff_count.sum() * 0.35), float(admin_neg), int(admin.case_id.nunique()), pct(admin.resolution_sla_breached))

    it = slices["it"]
    it_digital_pre = digital[(digital.service_key == 2) & (digital.date < "2025-10-01")]
    it_digital_post = digital[(digital.service_key == 2) & (digital.date >= "2025-10-01")]
    it_neg = joined_feedback[(joined_feedback.service_key_case == 2) & joined_feedback.category.isin(["Account access and login", "Multi-factor authentication"])]["csat_score"].lt(4).mean()
    add_action("ACT-002", 2, 0, 0, "Repeat contacts for account access and MFA", "Repeat-contact rate", pct(it.repeat_contact_14d), "Self-service completion", float(it_digital_pre.successful_completions.sum() / it_digital_pre.self_service_sessions.sum()), len(it), "Redesign account recovery guidance and expose status-aware next steps before case submission.", 5, "Self-service completion rate", float(it_digital_pre.successful_completions.sum() / it_digital_pre.self_service_sessions.sum()), 0.72, float(it_digital_post.successful_completions.sum() / it_digital_post.self_service_sessions.sum()), "%", "Completed", "High", "2026-10-15", float(it.repeat_contact_14d.sum() * 0.45), float(it_neg), int(it.case_id.nunique()), pct(it.resolution_sla_breached))

    fac = slices["fac"]
    fac_wo = work_orders[(work_orders.campus_key == 1) & work_orders.category.isin(["HVAC and temperature", "Study spaces"])]
    fac_neg = joined_feedback[(joined_feedback.service_key_case == 3) & (joined_feedback.campus_key_case == 1) & joined_feedback.category.isin(["HVAC and temperature", "Study spaces"])]["csat_score"].lt(4).mean()
    add_action("ACT-003", 3, 1, 0, "Facilities rework in high-demand study environments", "Contractor rework rate", pct(fac_wo.rework_flag), "On-time completion", pct(fac_wo.on_time_flag), len(fac_wo), "Introduce contractor quality checks and weekly hotspot review for HVAC and study-space work orders.", 9, "Contractor rework rate", pct(fac_wo[fac_wo.created_datetime < "2026-04-01"].rework_flag), 0.10, pct(fac_wo[fac_wo.created_datetime >= "2026-04-01"].rework_flag), "%", "In progress", "High", "2026-09-15", float(fac_wo.rework_flag.sum() * 1.5), float(fac_neg), int(fac.case_id.nunique()), pct(fac.resolution_sla_breached))

    peak_capacity = capacity[(capacity.service_key == 1) & capacity.week_start.dt.month.isin([2, 3, 7, 8])]
    gap_rate = pct(peak_capacity.capacity_gap_pct.gt(0.10))
    add_action("ACT-004", 1, 0, 0, "Predictable semester-start capacity shortfall", "Weeks above 10% gap", gap_rate, "Peak required hours", float(peak_capacity.required_handle_hours.max()), len(peak_capacity), "Move roster capacity into the four peak weeks and publish high-volume self-service guidance before semester start.", 1, "Weeks with capacity gap above 10%", gap_rate, 0.15, None, "%", "Planned", "High", "2027-01-15", float(peak_capacity.capacity_gap_hours.clip(lower=0).sum()), 0.28, int(peak_capacity.cases_received.sum()), 0.24)

    pg = slices["pg_int"]
    pg_fb = joined_feedback[joined_feedback.cohort_key_case == 4]
    add_action("ACT-005", 1, 0, 4, "Higher effort for postgraduate international students", "Negative experience rate", float(pg_fb.csat_score.lt(4).mean()), "Repeat-contact rate", pct(pg.repeat_contact_14d), len(pg), "Run a targeted journey review and test clearer guidance for enrolment and fee steps.", 1, "Negative experience rate", float(pg_fb.csat_score.lt(4).mean()), 0.25, None, "%", "Planned", "Medium", "2026-11-30", float(pg.repeat_contact_14d.sum() * 0.45), float(pg_fb.csat_score.lt(4).mean()), int(pg.case_id.nunique()), pct(pg.resolution_sla_breached))

    learning = slices["learning"]
    learning_fb = joined_feedback[(joined_feedback.service_key_case == 2) & (joined_feedback.category == "Learning platform")]
    add_action("ACT-006", 2, 0, 0, "Learning-platform demand spikes near assessment periods", "P90 resolution hours", float(learning.resolution_business_hours.quantile(0.9)), "Negative experience rate", float(learning_fb.csat_score.lt(4).mean()), len(learning), "Publish incident-aware guidance and pre-position Learning Technology coverage for assessment peaks.", 6, "P90 resolution business hours", float(learning.resolution_business_hours.quantile(0.9)), float(learning.resolution_business_hours.quantile(0.9) * 0.75), None, "business hours", "Planned", "Medium", "2026-10-31", float(learning.repeat_contact_14d.sum() * 0.45), float(learning_fb.csat_score.lt(4).mean()), int(learning.case_id.nunique()), pct(learning.resolution_sla_breached))

    lighting = resolved[(resolved.service_key == 3) & (resolved.category == "Security and lighting")]
    lighting_wo = work_orders[work_orders.category == "Security and lighting"]
    add_action("ACT-007", 3, 1, 0, "Lighting work orders require clearer escalation", "On-time completion", pct(lighting_wo.on_time_flag), "P90 completion hours", float(lighting_wo.completion_business_hours.quantile(0.9)), len(lighting_wo), "Create an explicit safety escalation path and monitor aged lighting work orders daily.", 9, "On-time completion rate", pct(lighting_wo.on_time_flag), 0.92, None, "%", "Planned", "Medium", "2026-09-30", float(lighting_wo.rework_flag.sum() * 1.2), 0.31, int(lighting.case_id.nunique()), pct(lighting.resolution_sla_breached))

    fees = slices["fees"]
    fees_fb = joined_feedback[(joined_feedback.service_key_case == 1) & (joined_feedback.category == "Fees and payments")]
    add_action("ACT-008", 1, 0, 0, "Fees enquiries create avoidable follow-up", "Repeat-contact rate", pct(fees.repeat_contact_14d), "Customer effort <=2", pct(fees_fb.ces_score.le(2)), len(fees), "Rewrite fee-status messages and add a single owner for complex payment enquiries.", 3, "Repeat-contact rate", pct(fees.repeat_contact_14d), max(0.08, pct(fees.repeat_contact_14d) * 0.75), None, "%", "Planned", "Medium", "2026-12-15", float(fees.repeat_contact_14d.sum() * 0.45), float(fees_fb.csat_score.lt(4).mean()), int(fees.case_id.nunique()), pct(fees.resolution_sla_breached))

    return pd.DataFrame(actions)


def add_raw_case_anomalies(cases: pd.DataFrame) -> pd.DataFrame:
    raw = cases.copy()
    missing_indices = RNG.choice(raw.index, size=120, replace=False)
    raw.loc[missing_indices, "team_key"] = np.nan

    spelling_map = {
        "Enrolment changes": "Enrollment Changes",
        "Timetable and class allocation": "Timetable & Class Allocation",
        "Wi-Fi and network": "Wifi / Network",
        "HVAC and temperature": "HVAC/Temperature",
    }
    anomaly_indices = RNG.choice(raw.index, size=140, replace=False)
    for idx in anomaly_indices:
        canonical = raw.at[idx, "category"]
        if canonical in spelling_map:
            raw.at[idx, "category"] = spelling_map[canonical]

    closed_candidates = raw[raw["closed_datetime"].notna()].sample(n=35, random_state=SEED)
    raw.loc[closed_candidates.index, "closed_datetime"] = raw.loc[closed_candidates.index, "submitted_datetime"] - pd.to_timedelta(4, unit="h")

    duplicates = raw.sample(n=100, random_state=SEED + 5).copy()
    duplicates["source_extract_ts"] = pd.Timestamp("2026-08-15 10:00:00")
    raw = pd.concat([raw, duplicates], ignore_index=True)
    return raw


def load_and_transform(raw_tables: dict[str, pd.DataFrame], dimensions: dict[str, pd.DataFrame]) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    connection = sqlite3.connect(DB_PATH)
    try:
        for name, df in {**raw_tables, **dimensions}.items():
            sql_ready = df.copy()
            for col in sql_ready.columns:
                if pd.api.types.is_datetime64_any_dtype(sql_ready[col]):
                    sql_ready[col] = sql_ready[col].dt.strftime("%Y-%m-%d %H:%M:%S")
            sql_ready.to_sql(name, connection, index=False, if_exists="replace")
        sql_text = (ROOT / "sql" / "transform_and_validate.sql").read_text(encoding="utf-8")
        connection.executescript(sql_text)
        connection.commit()

        curated_names = [
            "fact_case",
            "fact_case_event",
            "fact_interaction",
            "fact_feedback",
            "fact_capacity_weekly",
            "fact_work_order",
            "fact_digital_journey_daily",
            "fact_population_monthly",
            "fact_action_insight",
            "fact_demand_forecast",
            "forecast_model_evaluation",
            "dim_date_curated",
            "dim_service_curated",
            "dim_team_curated",
            "dim_campus_curated",
            "dim_cohort_curated",
            "dim_channel_curated",
            "dim_sla_curated",
            "dim_lifecycle_stage_curated",
            "data_quality_issues",
        ]
        for table_name in curated_names:
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", connection)
            output_name = table_name.replace("_curated", "") + ".csv"
            # Nullable keys come back as float; write them as integers so they match their dimension keys.
            key_columns = [c for c in df.columns if c.endswith("_key") and pd.api.types.is_float_dtype(df[c])]
            df[key_columns] = df[key_columns].astype("Int64")
            write_csv(df, CURATED_DIR / output_name)
    finally:
        connection.close()


def validation_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    connection = sqlite3.connect(DB_PATH)
    try:
        queries = {
            "Curated unique cases": "SELECT COUNT(*) FROM fact_case",
            "Case events": "SELECT COUNT(*) FROM fact_case_event",
            "Interactions": "SELECT COUNT(*) FROM fact_interaction",
            "Feedback responses": "SELECT COUNT(*) FROM fact_feedback",
            "Facilities work orders": "SELECT COUNT(*) FROM fact_work_order",
            "Action insights": "SELECT COUNT(*) FROM fact_action_insight",
            "Demand forecast rows": "SELECT COUNT(*) FROM fact_demand_forecast",
            "DQ issues recorded": "SELECT COUNT(*) FROM data_quality_issues",
            "Open backlog": "SELECT COUNT(*) FROM fact_case WHERE backlog_eligible_flag=1 AND current_status NOT IN ('Resolved')",
        }
        rows = []
        for metric, query in queries.items():
            value = connection.execute(query).fetchone()[0]
            rows.append({"check": metric, "value": value, "status": "PASS"})

        scenario_queries = [
            (
                "Admin assignment hours improved after routing intervention",
                """SELECT
                    ROUND(AVG(CASE WHEN submitted_datetime < '2026-02-01' THEN assignment_business_hours END),2),
                    ROUND(AVG(CASE WHEN submitted_datetime >= '2026-02-01' THEN assignment_business_hours END),2)
                    FROM fact_case WHERE service_key=1 AND category IN ('Enrolment changes','Timetable and class allocation')""",
                lambda a, b: b < a,
            ),
            (
                "IT repeat contacts reduced after self-service intervention",
                """SELECT
                    ROUND(AVG(CASE WHEN submitted_datetime < '2025-10-01' THEN repeat_contact_14d END),4),
                    ROUND(AVG(CASE WHEN submitted_datetime >= '2025-10-01' THEN repeat_contact_14d END),4)
                    FROM fact_case WHERE service_key=2 AND category IN ('Account access and login','Multi-factor authentication')""",
                lambda a, b: b < a,
            ),
            (
                "Facilities hotspot has elevated SLA breach",
                """SELECT
                    ROUND(AVG(CASE WHEN campus_key=1 AND category IN ('HVAC and temperature','Study spaces') THEN resolution_sla_breached END),4),
                    ROUND(AVG(CASE WHEN NOT (campus_key=1 AND category IN ('HVAC and temperature','Study spaces')) THEN resolution_sla_breached END),4)
                    FROM fact_case WHERE service_key=3 AND eligible_resolution_flag=1""",
                lambda a, b: a > b,
            ),
        ]
        scenario_rows = []
        for scenario, query, predicate in scenario_queries:
            before, after = connection.execute(query).fetchone()
            scenario_rows.append(
                {
                    "scenario": scenario,
                    "comparison_a": before,
                    "comparison_b": after,
                    "status": "PASS" if predicate(float(before), float(after)) else "FAIL",
                }
            )
        return pd.DataFrame(rows), pd.DataFrame(scenario_rows)
    finally:
        connection.close()


def main() -> None:
    ensure_dirs()
    dimensions = make_dimensions()
    cases = generate_cases()
    interactions, cases = generate_interactions(cases)
    events = generate_events(cases)
    work_orders = generate_work_orders(cases)
    feedback = generate_feedback(cases, work_orders)
    capacity = generate_capacity(cases)
    digital = generate_digital(cases)
    population = generate_population()
    forecast, forecast_evaluation = generate_demand_forecast(cases)
    actions = create_actions(cases, feedback, capacity, work_orders, digital)
    raw_cases = add_raw_case_anomalies(cases)

    raw_tables = {
        "raw_case": raw_cases,
        "raw_case_event": events,
        "raw_interaction": interactions,
        "raw_feedback": feedback,
        "raw_capacity_weekly": capacity,
        "raw_work_order": work_orders,
        "raw_digital_journey_daily": digital,
        "raw_population_monthly": population,
        "raw_action_insight": actions,
        "raw_demand_forecast": forecast,
        "raw_forecast_model_evaluation": forecast_evaluation,
    }
    for name, df in raw_tables.items():
        write_csv(df, RAW_DIR / f"{name}.csv")
    for name, df in dimensions.items():
        write_csv(df, RAW_DIR / f"{name}.csv")

    load_and_transform(raw_tables, dimensions)
    checks, scenarios = validation_summary()
    write_csv(checks, CURATED_DIR / "validation_summary.csv")
    write_csv(scenarios, CURATED_DIR / "seeded_scenario_validation.csv")

    manifest = {
        "generated_at": "2026-08-15T12:00:00+10:00",
        "seed": SEED,
        "period_start": str(START_DATE.date()),
        "period_end": str(END_DATE.date()),
        "synthetic_label": SYNTHETIC_LABEL,
        "raw_tables": {name: int(len(df)) for name, df in raw_tables.items()},
        "dimension_tables": {name: int(len(df)) for name, df in dimensions.items()},
        "validation_passed": bool((checks["status"] == "PASS").all() and (scenarios["status"] == "PASS").all()),
    }
    (CURATED_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
