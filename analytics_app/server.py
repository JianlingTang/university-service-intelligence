#!/usr/bin/env python3
"""Read-only analytics application for the synthetic service-intelligence model."""

from __future__ import annotations

import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "university_service_intelligence.db"
INDEX_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def service_filter(service_key: int | None, alias: str = "") -> tuple[str, tuple]:
    prefix = f"{alias}." if alias else ""
    if service_key is None:
        return "", ()
    return f" AND {prefix}service_key = ?", (service_key,)


def get_summary(service_key: int | None = None) -> dict:
    where, params = service_filter(service_key)
    with connect() as connection:
        case_row = connection.execute(
            f"""
            SELECT
                COUNT(DISTINCT case_id) AS cases_received,
                SUM(CASE WHEN current_status='Resolved' THEN 1 ELSE 0 END) AS cases_closed,
                SUM(CASE WHEN backlog_eligible_flag=1 THEN 1 ELSE 0 END) AS open_backlog,
                AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_sla_breached END) AS sla_breach_rate,
                AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_business_hours END) AS avg_resolution_hours,
                AVG(repeat_contact_14d) AS repeat_contact_rate,
                SUM(staff_handle_hours) AS staff_handle_hours,
                SUM(estimated_cost_aud) AS estimated_cost_aud
            FROM fact_case
            WHERE 1=1 {where}
            """,
            params,
        ).fetchone()
        feedback_row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS response_count,
                AVG(csat_positive_flag) AS csat_positive_rate,
                AVG(ces_score) AS average_effort
            FROM fact_feedback
            WHERE response_valid=1 AND feedback_type='Post-case survey' {where}
            """,
            params,
        ).fetchone()
        forecast_row = connection.execute(
            f"""
            SELECT
                SUM(predicted_cases) AS forecast_cases,
                SUM(predicted_capacity_gap_hours) AS forecast_gap_hours
            FROM fact_demand_forecast
            WHERE record_type='Forecast' {where}
            """,
            params,
        ).fetchone()
        dq_count = connection.execute("SELECT COUNT(*) FROM data_quality_issues").fetchone()[0]
    result = dict(case_row)
    result.update(dict(feedback_row))
    result.update(dict(forecast_row))
    result["sla_compliance_rate"] = 1 - (result.pop("sla_breach_rate") or 0)
    result["data_quality_issues"] = dq_count
    result["synthetic"] = True
    return result


def get_actions(service_key: int | None = None) -> list[dict]:
    where, params = service_filter(service_key, "a")
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT
                a.action_id,
                s.service_name,
                a.issue,
                a.recommended_action,
                t.team_name AS owner,
                a.priority,
                a.action_status,
                a.sample_size,
                a.evidence_1_name,
                a.evidence_1_value,
                a.evidence_2_name,
                a.evidence_2_value,
                a.next_review_date,
                a.estimated_avoidable_staff_hours
            FROM fact_action_insight a
            LEFT JOIN dim_service_curated s ON s.service_key=a.service_key
            LEFT JOIN dim_team_curated t ON t.team_key=a.suggested_owner_team_key
            WHERE 1=1 {where}
            ORDER BY CASE a.priority WHEN 'High' THEN 1 ELSE 2 END, a.estimated_avoidable_staff_hours DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_forecast(service_key: int | None = None) -> list[dict]:
    where, params = service_filter(service_key, "f")
    with connect() as connection:
        rows = connection.execute(
            f"""
            SELECT
                f.week_start,
                s.service_name,
                f.predicted_cases,
                f.lower_95_cases,
                f.upper_95_cases,
                f.predicted_handle_hours,
                f.typical_capacity_hours,
                f.predicted_capacity_gap_hours
            FROM fact_demand_forecast f
            JOIN dim_service_curated s ON s.service_key=f.service_key
            WHERE f.record_type='Forecast' {where}
            ORDER BY f.week_start, f.service_key
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def run_scenario(service_key: int, demand_change_pct: float, capacity_change_pct: float) -> dict:
    forecast = get_forecast(service_key)
    adjusted = []
    for row in forecast:
        demand_hours = row["predicted_handle_hours"] * (1 + demand_change_pct / 100)
        capacity_hours = row["typical_capacity_hours"] * (1 + capacity_change_pct / 100)
        adjusted.append(
            {
                "week_start": row["week_start"],
                "demand_hours": round(demand_hours, 2),
                "capacity_hours": round(capacity_hours, 2),
                "gap_hours": round(demand_hours - capacity_hours, 2),
            }
        )
    return {
        "service_key": service_key,
        "demand_change_pct": demand_change_pct,
        "capacity_change_pct": capacity_change_pct,
        "total_gap_hours": round(sum(max(0, row["gap_hours"]) for row in adjusted), 2),
        "weeks_over_capacity": sum(row["gap_hours"] > 0 for row in adjusted),
        "weeks": adjusted,
        "synthetic": True,
    }


class AnalyticsHandler(BaseHTTPRequestHandler):
    def send_json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        service_key = int(query["service_key"][0]) if query.get("service_key") else None
        try:
            if parsed.path == "/":
                payload = INDEX_PATH.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            elif parsed.path == "/api/summary":
                self.send_json(get_summary(service_key))
            elif parsed.path == "/api/actions":
                self.send_json(get_actions(service_key))
            elif parsed.path == "/api/forecast":
                self.send_json(get_forecast(service_key))
            else:
                self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, sqlite3.Error) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/scenario":
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length) or b"{}")
            result = run_scenario(
                int(request.get("service_key", 1)),
                float(request.get("demand_change_pct", 0)),
                float(request.get("capacity_change_pct", 0)),
            )
            self.send_json(result)
        except (ValueError, TypeError, json.JSONDecodeError, sqlite3.Error) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("Database not found. Run scripts/generate_synthetic_data.py first.")
    server = ThreadingHTTPServer(("127.0.0.1", 8765), AnalyticsHandler)
    print("Analytics Action Console: http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()

