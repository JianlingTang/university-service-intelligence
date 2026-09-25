#!/usr/bin/env python3
"""Render four portfolio-ready dashboard mockups from curated synthetic data."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    HAVE_MATPLOTLIB = True
except ModuleNotFoundError:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_MATPLOTLIB = False


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "university_service_intelligence.db"
OUT = ROOT / "mockups"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#102A43"
BLUE = "#156B8A"
TEAL = "#2A9D8F"
AMBER = "#E9A23B"
RED = "#C84630"
MUTED = "#627D98"
LIGHT = "#F5F7FA"
LINE = "#D9E2EC"
WHITE = "#FFFFFF"


def query(sql: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        return pd.read_sql_query(sql, connection)


def base_page(title: str, question: str):
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=LIGHT)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.add_patch(Rectangle((0, 0.91), 1, 0.09, facecolor=NAVY, transform=ax.transAxes, clip_on=False))
    ax.text(0.028, 0.96, title, color=WHITE, fontsize=22, fontweight="bold", va="center", transform=ax.transAxes)
    ax.text(0.028, 0.925, question, color="#D9EAF2", fontsize=10.5, va="center", transform=ax.transAxes)
    ax.text(0.972, 0.96, "SYNTHETIC DEMONSTRATION DATA", ha="right", va="center", color="#FFE7B3", fontsize=9, fontweight="bold", transform=ax.transAxes)
    ax.text(0.972, 0.925, "Sep 2024 - 15 Aug 2026  |  All services", ha="right", va="center", color="#D9EAF2", fontsize=8.5, transform=ax.transAxes)
    return fig, ax


def panel(fig, x, y, w, h, title=None):
    ax_bg = fig.add_axes([x, y, w, h])
    ax_bg.set_axis_off()
    ax_bg.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.005,rounding_size=0.018", facecolor=WHITE, edgecolor=LINE, linewidth=1, transform=ax_bg.transAxes))
    if title:
        ax_bg.text(0.035, 0.94, title, fontsize=10.5, fontweight="bold", color=NAVY, va="top", transform=ax_bg.transAxes)
    return ax_bg


def chart_axis(fig, x, y, w, h):
    ax = fig.add_axes([x, y, w, h], facecolor=WHITE)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="y", color=LINE, linewidth=0.8, alpha=0.75)
    ax.set_axisbelow(True)
    return ax


def fmt_int(value):
    return f"{int(round(value)):,}"


def metric_cards(fig, values):
    x0, gap, width, y, h = 0.028, 0.009, 0.149, 0.795, 0.095
    for i, (label, value, context, status) in enumerate(values):
        x = x0 + i * (width + gap)
        ax = panel(fig, x, y, width, h)
        ax.text(0.07, 0.72, label, color=MUTED, fontsize=8.5, va="center", transform=ax.transAxes)
        ax.text(0.07, 0.40, value, color=NAVY, fontsize=19, fontweight="bold", va="center", transform=ax.transAxes)
        color = TEAL if status == "good" else AMBER if status == "warn" else RED
        ax.add_patch(FancyBboxPatch((0.07, 0.10), 0.035, 0.08, boxstyle="round,pad=0.01", facecolor=color, edgecolor="none", transform=ax.transAxes))
        ax.text(0.13, 0.14, context, color=MUTED, fontsize=7.4, va="center", transform=ax.transAxes)


def executive_page():
    summary = query("""
        SELECT COUNT(*) cases,
               SUM(CASE WHEN backlog_eligible_flag=1 THEN 1 ELSE 0 END) backlog,
               1-AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_sla_breached END) sla,
               AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_business_hours END) avg_resolution,
               SUM(staff_handle_hours) staff_hours
        FROM fact_case
    """).iloc[0]
    csat = query("SELECT AVG(csat_positive_flag) value, COUNT(*) n FROM fact_feedback WHERE feedback_type='Post-case survey'").iloc[0]
    forecast_gap = query("SELECT SUM(CASE WHEN predicted_capacity_gap_hours>0 THEN predicted_capacity_gap_hours ELSE 0 END) gap FROM fact_demand_forecast WHERE record_type='Forecast'").iloc[0, 0]
    fig, _ = base_page("Executive Operational Health", "Where should leaders act first to reduce service friction and avoidable workload?")
    metric_cards(fig, [
        ("Cases received", fmt_int(summary.cases), "24-month demand", "good"),
        ("Open backlog", fmt_int(summary.backlog), "current workload", "good"),
        ("SLA compliance", f"{summary.sla:.1%}", "eligible cases", "warn"),
        ("Avg resolution", f"{summary.avg_resolution:.1f}h", "business hours", "warn"),
        ("CSAT positive", f"{csat.value:.1%}", f"n={int(csat.n):,}", "warn"),
        ("Forecast gap", f"{forecast_gap:,.0f}h", "next 12 weeks", "bad"),
    ])

    panel(fig, 0.028, 0.37, 0.49, 0.39, "Demand and throughput move with the academic calendar")
    monthly = query("""
        SELECT substr(submitted_datetime,1,7) month,
               COUNT(*) received,
               SUM(CASE WHEN current_status='Resolved' THEN 1 ELSE 0 END) closed
        FROM fact_case GROUP BY 1 ORDER BY 1
    """)
    ax = chart_axis(fig, 0.063, 0.425, 0.42, 0.27)
    x = np.arange(len(monthly))
    ax.plot(x, monthly.received, color=BLUE, linewidth=2.6, label="Received")
    ax.plot(x, monthly.closed, color=TEAL, linewidth=2.2, label="Closed")
    ax.fill_between(x, monthly.received, monthly.closed, where=monthly.received >= monthly.closed, color=AMBER, alpha=0.12)
    ax.set_xticks(x[::3], monthly.month.iloc[::3].str[2:], rotation=0)
    ax.legend(frameon=False, loc="upper left", fontsize=8, ncol=2)
    ax.set_ylabel("Cases", color=MUTED, fontsize=8)

    panel(fig, 0.535, 0.37, 0.437, 0.39, "Priority matrix: experience friction versus avoidable effort")
    actions = query("""SELECT a.*, t.team_name AS owner
        FROM fact_action_insight a
        JOIN dim_team_curated t ON t.team_key=a.suggested_owner_team_key
        ORDER BY a.estimated_avoidable_staff_hours DESC""")
    ax = chart_axis(fig, 0.575, 0.425, 0.36, 0.27)
    sizes = 80 + 420 * actions.users_affected / actions.users_affected.max()
    colours = np.where(actions.sla_breach_rate >= 0.3, RED, np.where(actions.sla_breach_rate >= 0.2, AMBER, TEAL))
    ax.scatter(actions.estimated_avoidable_staff_hours, actions.negative_experience_rate * 100, s=sizes, c=colours, alpha=0.78, edgecolor=WHITE, linewidth=1)
    for row in actions.nlargest(4, "estimated_avoidable_staff_hours").itertuples():
        ax.annotate(row.action_id, (row.estimated_avoidable_staff_hours, row.negative_experience_rate * 100), xytext=(4, 4), textcoords="offset points", fontsize=7.5, color=NAVY)
    ax.set_xlabel("Estimated avoidable staff hours", fontsize=8, color=MUTED)
    ax.set_ylabel("Negative experience (%)", fontsize=8, color=MUTED)

    action_panel = panel(fig, 0.028, 0.055, 0.944, 0.28, "Top evidence-backed actions")
    top = actions.sort_values(["priority", "estimated_avoidable_staff_hours"], ascending=[True, False]).head(3)
    for i, row in enumerate(top.itertuples()):
        y = 0.72 - i * 0.25
        action_panel.text(0.035, y, row.action_id, color=RED if row.priority == "High" else AMBER, fontsize=9, fontweight="bold", transform=action_panel.transAxes)
        action_panel.text(0.11, y, row.issue, color=NAVY, fontsize=9.2, fontweight="bold", transform=action_panel.transAxes)
        evidence = f"{row.evidence_1_name}: {row.evidence_1_value:.1%}  |  {row.evidence_2_name}: {row.evidence_2_value:.1%}  |  n={row.sample_size:,}"
        action_panel.text(0.11, y - 0.08, evidence, color=MUTED, fontsize=7.8, transform=action_panel.transAxes)
        action_panel.text(0.55, y, row.recommended_action, color="#334E68", fontsize=8.2, transform=action_panel.transAxes)
        if i < 2:
            action_panel.plot([0.03, 0.97], [y - 0.14, y - 0.14], color=LINE, linewidth=0.8, transform=action_panel.transAxes)
    fig.savefig(OUT / "01-executive-operational-health.png", facecolor=LIGHT, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def bottlenecks_page():
    fig, _ = base_page("Bottlenecks & Capacity", "Where does work wait, and when will demand exceed productive capacity?")
    stage = query("""SELECT s.service_name,
        AVG(c.triage_business_hours) triage,
        AVG(c.assignment_business_hours) assignment,
        AVG(CASE WHEN c.eligible_resolution_flag=1 THEN c.resolution_business_hours END) resolution
        FROM fact_case c JOIN dim_service_curated s USING(service_key) GROUP BY 1""")
    cap = query("""SELECT week_start, SUM(required_handle_hours) required, SUM(staffed_hours) staffed
        FROM fact_capacity_weekly GROUP BY 1 ORDER BY 1""")
    forecast = query("""SELECT week_start, SUM(predicted_handle_hours) demand, SUM(typical_capacity_hours) capacity,
        SUM(lower_95_cases) lower_cases, SUM(upper_95_cases) upper_cases, SUM(predicted_cases) predicted_cases
        FROM fact_demand_forecast WHERE record_type='Forecast' GROUP BY 1 ORDER BY 1""")
    work = query("""SELECT contractor_name, AVG(on_time_flag) on_time, AVG(rework_flag) rework, COUNT(*) n
        FROM fact_work_order GROUP BY 1 ORDER BY on_time""")
    open_cases = query("SELECT submitted_datetime FROM fact_case WHERE backlog_eligible_flag=1")
    open_cases["age"] = (pd.Timestamp("2026-08-15") - pd.to_datetime(open_cases.submitted_datetime)).dt.days
    age_bins = pd.cut(open_cases.age, [-1, 7, 14, 30, 10_000], labels=["0-7d", "8-14d", "15-30d", "30d+"]).value_counts().reindex(["0-7d", "8-14d", "15-30d", "30d+"])

    panel(fig, 0.028, 0.51, 0.30, 0.38, "Assignment is the controllable wait stage")
    ax = chart_axis(fig, 0.07, 0.565, 0.22, 0.24)
    y = np.arange(len(stage))
    ax.barh(y, stage.triage, color="#9FBFCC", label="Triage")
    ax.barh(y, stage.assignment, left=stage.triage, color=AMBER, label="Assignment")
    ax.barh(y, stage.resolution, left=stage.triage + stage.assignment, color=BLUE, label="Resolution")
    ax.set_yticks(y, stage.service_name.str.replace("Student Administration", "Student Admin"))
    ax.invert_yaxis(); ax.legend(frameon=False, fontsize=7, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.28))
    ax.set_xlabel("Average business hours", fontsize=8, color=MUTED)

    panel(fig, 0.345, 0.51, 0.22, 0.38, "Current backlog age")
    ax = chart_axis(fig, 0.38, 0.565, 0.15, 0.24)
    colors = [TEAL, BLUE, AMBER, RED]
    ax.bar(age_bins.index, age_bins.values, color=colors)
    ax.set_ylabel("Open cases", fontsize=8, color=MUTED)
    for i, v in enumerate(age_bins.values): ax.text(i, v + 2, str(v), ha="center", color=NAVY, fontsize=8)

    panel(fig, 0.582, 0.51, 0.39, 0.38, "Contractor quality varies by provider")
    ax = chart_axis(fig, 0.625, 0.565, 0.31, 0.24)
    y = np.arange(len(work))
    ax.barh(y - 0.13, work.on_time * 100, height=0.24, color=TEAL, label="On time")
    ax.barh(y + 0.13, work.rework * 100, height=0.24, color=RED, label="Rework")
    ax.set_yticks(y, work.contractor_name.str.replace("Learning Spaces Technical", "Learning Spaces Tech"))
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("Rate (%)", fontsize=8, color=MUTED)
    ax.legend(frameon=False, fontsize=7, loc="lower right")

    panel(fig, 0.028, 0.055, 0.48, 0.42, "Required work exceeded capacity in predictable peaks")
    ax = chart_axis(fig, 0.067, 0.115, 0.40, 0.28)
    x = np.arange(len(cap)); ax.plot(x, cap.required, color=BLUE, linewidth=2, label="Required hours"); ax.plot(x, cap.staffed, color=AMBER, linewidth=1.8, label="Staffed hours")
    ax.fill_between(x, cap.required, cap.staffed, where=cap.required > cap.staffed, color=RED, alpha=0.12)
    ax.set_xticks(x[::13], pd.to_datetime(cap.week_start).dt.strftime("%b %y").iloc[::13]); ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.set_ylabel("Hours/week", fontsize=8, color=MUTED)

    panel(fig, 0.525, 0.055, 0.447, 0.42, "12-week outlook includes uncertainty and model quality")
    ax = chart_axis(fig, 0.565, 0.13, 0.37, 0.25)
    x = np.arange(len(forecast)); ax.plot(x, forecast.demand, color=BLUE, linewidth=2.4, marker="o", markersize=3, label="Predicted demand hours"); ax.plot(x, forecast.capacity, color=AMBER, linewidth=2, linestyle="--", label="Typical capacity")
    ax.fill_between(x, forecast.demand * 0.86, forecast.demand * 1.14, color=BLUE, alpha=0.10)
    ax.set_xticks(x[::2], pd.to_datetime(forecast.week_start).dt.strftime("%d %b").iloc[::2]); ax.legend(frameon=False, fontsize=8, loc="upper left")
    evals = query("SELECT AVG(wape) wape FROM forecast_model_evaluation").iloc[0,0]
    ax.text(0.98, 0.94, f"Holdout WAPE {evals:.1%}", ha="right", va="top", transform=ax.transAxes, color=MUTED, fontsize=8)
    fig.savefig(OUT / "02-bottlenecks-and-capacity.png", facecolor=LIGHT, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def experience_page():
    fig, _ = base_page("Experience & Equity", "Which users experience disproportionate effort, and does operational friction explain the pattern?")
    service_exp = query("""SELECT s.service_name, AVG(f.csat_positive_flag) csat, AVG(f.ces_score) ces, COUNT(*) n
        FROM fact_feedback f JOIN dim_service_curated s USING(service_key)
        WHERE f.feedback_type='Post-case survey' GROUP BY 1 ORDER BY csat""")
    cohort_cases = query("""SELECT c.cohort_key, d.cohort_name, COUNT(*) cases
        FROM fact_case c JOIN dim_cohort_curated d USING(cohort_key) GROUP BY 1,2""")
    population = query("SELECT cohort_key, AVG(active_users) population FROM (SELECT month_start, cohort_key, SUM(active_users) active_users FROM fact_population_monthly GROUP BY 1,2) GROUP BY 1")
    cohort = cohort_cases.merge(population, on="cohort_key"); cohort["rate"] = cohort.cases / cohort.population * 1000; cohort = cohort.sort_values("rate")
    bands = query("""SELECT c.resolution_time_band, AVG(f.csat_positive_flag) csat, COUNT(*) n
        FROM fact_feedback f JOIN fact_case c ON c.case_id=f.related_case_id
        WHERE f.feedback_type='Post-case survey' GROUP BY 1""")
    order = ["0-8h", "9-24h", "25-80h", "80h+"]; bands["ord"] = bands.resolution_time_band.map({v:i for i,v in enumerate(order)}); bands = bands.sort_values("ord")
    themes = query("""SELECT feedback_theme, COUNT(*) n, AVG(csat_positive_flag) csat
        FROM fact_feedback WHERE feedback_type='Post-case survey' GROUP BY 1 ORDER BY n DESC""")
    digital = query("""SELECT substr(d.date,1,7) month, d.service_key, AVG(d.completion_rate) completion,
        AVG(c.repeat_contact_14d) repeat_rate
        FROM fact_digital_journey_daily d JOIN fact_case c ON substr(c.submitted_datetime,1,10)=substr(d.date,1,10) AND c.service_key=d.service_key
        GROUP BY 1,2 ORDER BY 1""")

    panel(fig, 0.028, 0.52, 0.31, 0.37, "Service experience: satisfaction and effort")
    ax = chart_axis(fig, 0.07, 0.575, 0.23, 0.23)
    y=np.arange(len(service_exp)); ax.barh(y, service_exp.csat*100, color=[RED,AMBER,TEAL]); ax.set_yticks(y,service_exp.service_name.str.replace("Student Administration","Student Admin")); ax.invert_yaxis(); ax.set_xlim(0,100); ax.set_xlabel("CSAT positive (%)",fontsize=8,color=MUTED)
    for i,r in enumerate(service_exp.itertuples()): ax.text(r.csat*100+1,i,f"{r.csat:.0%}  n={r.n:,}",va="center",fontsize=8,color=NAVY)

    panel(fig, 0.355, 0.52, 0.33, 0.37, "Population-adjusted demand reveals hidden gaps")
    ax = chart_axis(fig, 0.40, 0.575, 0.245, 0.23)
    short = cohort.cohort_name.str.replace("Postgraduate Coursework ","PG ").str.replace("Undergraduate ","UG ").str.replace("Higher Degree Research","HDR")
    ax.barh(np.arange(len(cohort)), cohort.rate, color=np.where(cohort.cohort_key==4,RED,BLUE)); ax.set_yticks(np.arange(len(cohort)),short); ax.set_xlabel("Cases per 1,000 active users",fontsize=8,color=MUTED)

    panel(fig, 0.702, 0.52, 0.27, 0.37, "Long resolution is associated with lower CSAT")
    ax = chart_axis(fig, 0.745, 0.575, 0.19, 0.23)
    ax.plot(bands.resolution_time_band, bands.csat*100,color=BLUE,marker="o",linewidth=2.4); ax.set_ylim(0,100); ax.set_ylabel("CSAT positive (%)",fontsize=8,color=MUTED)
    for i,r in enumerate(bands.itertuples()): ax.text(i,r.csat*100+4,f"n={r.n:,}",ha="center",fontsize=7,color=MUTED)

    panel(fig, 0.028, 0.055, 0.39, 0.42, "Feedback volume and dissatisfaction by theme")
    ax = chart_axis(fig, 0.075, 0.115, 0.30, 0.28)
    y=np.arange(len(themes)); ax.barh(y,themes.n,color=BLUE,alpha=.8); ax.set_yticks(y,themes.feedback_theme); ax.invert_yaxis(); ax.set_xlabel("Responses",fontsize=8,color=MUTED)
    for i,r in enumerate(themes.itertuples()): ax.text(r.n+10,i,f"{1-r.csat:.0%} negative",va="center",fontsize=7.5,color=RED)

    panel(fig, 0.435, 0.055, 0.537, 0.42, "Digital completion improved while requester repeat contact fell")
    ax = chart_axis(fig, 0.48, 0.115, 0.45, 0.28)
    for service_key,color,label in [(1,BLUE,"Student Admin completion"),(2,TEAL,"IT completion")]:
        sub=digital[digital.service_key==service_key]; ax.plot(np.arange(len(sub)),sub.completion*100,color=color,linewidth=2,label=label)
    it=digital[digital.service_key==2]; ax.plot(np.arange(len(it)),it.repeat_rate*100,color=RED,linewidth=1.8,linestyle="--",label="IT repeat contact")
    ax.set_xticks(np.arange(len(it))[::3],it.month.iloc[::3].str[2:]); ax.set_ylabel("Rate (%)",fontsize=8,color=MUTED); ax.legend(frameon=False,fontsize=8,ncol=2,loc="upper left")
    fig.savefig(OUT / "03-experience-and-equity.png", facecolor=LIGHT, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def actions_page():
    fig, _ = base_page("Actions & Benefits", "What should change, who owns it, and how will improvement be measured?")
    actions = query("""SELECT a.*, s.service_name, t.team_name owner FROM fact_action_insight a
        JOIN dim_service_curated s USING(service_key) JOIN dim_team_curated t ON t.team_key=a.suggested_owner_team_key
        ORDER BY CASE a.priority WHEN 'High' THEN 1 ELSE 2 END, a.estimated_avoidable_staff_hours DESC""")
    dq = query("SELECT issue_type, COUNT(*) n FROM data_quality_issues GROUP BY 1 ORDER BY n DESC")
    wape = query("SELECT service_key,wape FROM forecast_model_evaluation ORDER BY service_key")
    completed = int((actions.action_status == "Completed").sum()); in_progress = int((actions.action_status == "In progress").sum()); planned = int((actions.action_status == "Planned").sum())
    metric_cards(fig, [
        ("Actions tracked", str(len(actions)), "evidence-backed", "good"),
        ("Completed", str(completed), "benefit measured", "good"),
        ("In progress", str(in_progress), "owner assigned", "warn"),
        ("Planned", str(planned), "review scheduled", "warn"),
        ("Avoidable effort", f"{actions.estimated_avoidable_staff_hours.sum():,.0f}h", "opportunity estimate", "bad"),
        ("Users affected", f"{actions.users_affected.sum():,}", "not unique across actions", "warn"),
    ])
    table = panel(fig,0.028,0.29,0.65,0.47,"Action register: direct evidence, accountability and review")
    headers=[("Priority",.03),("Issue / evidence",.12),("Owner",.57),("Status",.72),("Review",.86)]
    for label,x in headers: table.text(x,.86,label,fontsize=8,color=MUTED,fontweight="bold",transform=table.transAxes)
    for i,row in enumerate(actions.head(6).itertuples()):
        y=.75-i*.115
        table.text(.03,y,row.priority,fontsize=8,color=RED if row.priority=="High" else AMBER,fontweight="bold",transform=table.transAxes)
        table.text(.12,y,row.issue[:58],fontsize=8.1,color=NAVY,fontweight="bold",transform=table.transAxes)
        table.text(.12,y-.045,f"{row.evidence_1_name}: {row.evidence_1_value:.1%} | n={row.sample_size:,}",fontsize=7,color=MUTED,transform=table.transAxes)
        table.text(.57,y,row.owner,fontsize=7.5,color="#334E68",transform=table.transAxes)
        table.text(.72,y,row.action_status,fontsize=7.5,color=TEAL if row.action_status=="Completed" else AMBER,transform=table.transAxes)
        table.text(.86,y,str(row.next_review_date)[:10],fontsize=7.5,color="#334E68",transform=table.transAxes)
        table.plot([.03,.97],[y-.068,y-.068],color=LINE,linewidth=.7,transform=table.transAxes)

    panel(fig,0.695,0.29,0.277,0.47,"Baseline, target and actual")
    ax=chart_axis(fig,.735,.36,.20,.31)
    completed_actions=actions[actions.actual_value.notna()].head(3).copy()
    y=np.arange(len(completed_actions)); ax.barh(y,completed_actions.baseline_value,color="#C7D6E0",height=.55,label="Baseline"); ax.scatter(completed_actions.target_value,y,color=AMBER,s=70,marker="|",linewidth=3,label="Target"); ax.scatter(completed_actions.actual_value,y,color=TEAL,s=52,marker="o",label="Actual")
    ax.set_yticks(y,completed_actions.action_id); ax.invert_yaxis(); ax.legend(frameon=False,fontsize=7,loc="lower center",bbox_to_anchor=(.5,-.32),ncol=3)
    ax.set_xlabel("Metric value (native unit)",fontsize=8,color=MUTED)

    health=panel(fig,.028,.055,.944,.20,"Data health and model assurance are visible, not hidden")
    x_positions=[.04,.30,.56,.78]
    health.text(x_positions[0],.56,"Data-quality issues",fontsize=8,color=MUTED,transform=health.transAxes); health.text(x_positions[0],.28,f"{dq.n.sum():,}",fontsize=20,color=NAVY,fontweight="bold",transform=health.transAxes)
    health.text(x_positions[1],.56,"Largest issue type",fontsize=8,color=MUTED,transform=health.transAxes); health.text(x_positions[1],.28,str(dq.iloc[0].issue_type),fontsize=11,color=NAVY,fontweight="bold",transform=health.transAxes)
    health.text(x_positions[2],.56,"Forecast holdout WAPE",fontsize=8,color=MUTED,transform=health.transAxes); health.text(x_positions[2],.28,f"{wape.wape.mean():.1%}",fontsize=20,color=NAVY,fontweight="bold",transform=health.transAxes)
    health.text(x_positions[3],.56,"Governance status",fontsize=8,color=MUTED,transform=health.transAxes); health.text(x_positions[3],.28,"Reconciled",fontsize=20,color=TEAL,fontweight="bold",transform=health.transAxes)
    fig.savefig(OUT / "04-actions-and-benefits.png", facecolor=LIGHT, bbox_inches="tight", pad_inches=0)
    plt.close(fig)


def pil_font(size: int, bold: bool = False):
    name = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"
    return ImageFont.truetype(name, size)


def pil_page(title: str, subtitle: str):
    image = Image.new("RGB", (1600, 900), LIGHT)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1600, 86), fill=NAVY)
    draw.text((38, 20), title, fill=WHITE, font=pil_font(28, True))
    draw.text((38, 56), subtitle, fill="#D9EAF2", font=pil_font(13))
    draw.text((1558, 25), "SYNTHETIC DEMONSTRATION DATA", fill="#FFE7B3", font=pil_font(12, True), anchor="ra")
    draw.text((1558, 55), "Sep 2024 - 15 Aug 2026 | All services", fill="#D9EAF2", font=pil_font(11), anchor="ra")
    return image, draw


def pil_panel(draw, box, title: str = ""):
    draw.rounded_rectangle(box, radius=10, fill=WHITE, outline=LINE, width=1)
    if title:
        draw.text((box[0] + 18, box[1] + 13), title, fill=NAVY, font=pil_font(14, True))


def pil_metrics(draw, metrics):
    x, y, w, gap = 40, 106, 240, 16
    for label, value, context, status in metrics:
        pil_panel(draw, (x, y, x + w, y + 92))
        draw.text((x + 15, y + 12), label, fill=MUTED, font=pil_font(11))
        draw.text((x + 15, y + 35), value, fill=NAVY, font=pil_font(24, True))
        colour = TEAL if status == "good" else AMBER if status == "warn" else RED
        draw.ellipse((x + 15, y + 70, x + 23, y + 78), fill=colour)
        draw.text((x + 30, y + 66), context, fill=MUTED, font=pil_font(10))
        x += w + gap


def pil_line_chart(draw, box, series, colors, labels):
    x0, y0, x1, y1 = box
    left, top, right, bottom = x0 + 52, y0 + 46, x1 - 22, y1 - 36
    draw.line((left, top, left, bottom), fill=LINE, width=2)
    draw.line((left, bottom, right, bottom), fill=LINE, width=2)
    max_value = max(max(values) for values in series) * 1.08 or 1
    count = max(len(values) for values in series)
    for values, color, label in zip(series, colors, labels):
        points = []
        for i, value in enumerate(values):
            px = left + i * (right - left) / max(count - 1, 1)
            py = bottom - value / max_value * (bottom - top)
            points.append((px, py))
        draw.line(points, fill=color, width=4)
    lx = left
    for color, label in zip(colors, labels):
        draw.line((lx, y0 + 28, lx + 24, y0 + 28), fill=color, width=4)
        draw.text((lx + 30, y0 + 20), label, fill=MUTED, font=pil_font(10))
        lx += 170


def pil_bar_chart(draw, box, labels, values, colors=None, percent=False):
    x0, y0, x1, y1 = box
    left, top, right, bottom = x0 + 200, y0 + 52, x1 - 30, y1 - 25
    max_value = max(values) * 1.15 or 1
    row_h = (bottom - top) / max(len(values), 1)
    for i, (label, value) in enumerate(zip(labels, values)):
        py = top + i * row_h + row_h * 0.18
        colour = colors[i] if colors else BLUE
        draw.text((x0 + 18, py), str(label)[:27], fill=MUTED, font=pil_font(10))
        draw.rounded_rectangle((left, py, left + (right - left) * value / max_value, py + row_h * 0.50), radius=4, fill=colour)
        text = f"{value:.0%}" if percent else f"{value:,.1f}"
        draw.text((left + (right - left) * value / max_value + 8, py), text, fill=NAVY, font=pil_font(10, True))


def pil_table(draw, box, rows, columns):
    x0, y0, x1, y1 = box
    widths = [int((x1 - x0) * fraction) for _, fraction in columns]
    x = x0 + 18
    for (label, _), width in zip(columns, widths):
        draw.text((x, y0 + 44), label, fill=MUTED, font=pil_font(10, True)); x += width
    row_y = y0 + 72
    for row in rows:
        x = x0 + 18
        for value, width in zip(row, widths):
            draw.text((x, row_y), str(value)[:48], fill=NAVY, font=pil_font(10)); x += width
        draw.line((x0 + 18, row_y + 24, x1 - 18, row_y + 24), fill=LINE, width=1)
        row_y += 50


def create_pil_mockups():
    summary = query("SELECT COUNT(*) cases, SUM(backlog_eligible_flag) backlog, 1-AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_sla_breached END) sla, AVG(CASE WHEN eligible_resolution_flag=1 THEN resolution_business_hours END) resolution FROM fact_case").iloc[0]
    csat = query("SELECT AVG(csat_positive_flag) value, COUNT(*) n FROM fact_feedback WHERE feedback_type='Post-case survey'").iloc[0]
    forecast_gap = query("SELECT SUM(CASE WHEN predicted_capacity_gap_hours>0 THEN predicted_capacity_gap_hours ELSE 0 END) gap FROM fact_demand_forecast WHERE record_type='Forecast'").iloc[0, 0]
    metrics = [("Cases received", fmt_int(summary.cases), "24-month demand", "good"),("Open backlog", fmt_int(summary.backlog), "current workload", "good"),("SLA compliance", f"{summary.sla:.1%}", "eligible cases", "warn"),("Avg resolution", f"{summary.resolution:.1f}h", "business hours", "warn"),("CSAT positive", f"{csat.value:.1%}", f"n={int(csat.n):,}", "warn"),("Forecast gap", f"{forecast_gap:,.0f}h", "next 12 weeks", "bad")]

    image, draw = pil_page("Executive Operational Health", "Where should leaders act first to reduce service friction and avoidable workload?")
    pil_metrics(draw, metrics)
    monthly = query("SELECT substr(submitted_datetime,1,7) month, COUNT(*) received, SUM(current_status='Resolved') closed FROM fact_case GROUP BY 1 ORDER BY 1")
    pil_panel(draw, (40, 220, 820, 565), "Demand and throughput follow the academic calendar")
    pil_line_chart(draw, (40, 220, 820, 565), [monthly.received.tolist(), monthly.closed.tolist()], [BLUE, TEAL], ["Received", "Closed"])
    actions = query("""SELECT a.*, t.team_name AS owner
        FROM fact_action_insight a
        JOIN dim_team_curated t ON t.team_key=a.suggested_owner_team_key
        ORDER BY a.estimated_avoidable_staff_hours DESC""")
    pil_panel(draw, (842, 220, 1560, 565), "Priority matrix: experience friction vs avoidable effort")
    x0,y0,x1,y1=900,285,1515,525; draw.line((x0,y1,x1,y1),fill=LINE,width=2); draw.line((x0,y0,x0,y1),fill=LINE,width=2)
    max_x=actions.estimated_avoidable_staff_hours.max()*1.1; max_y=actions.negative_experience_rate.max()*1.15
    for row in actions.itertuples():
        px=x0+row.estimated_avoidable_staff_hours/max_x*(x1-x0); py=y1-row.negative_experience_rate/max_y*(y1-y0); radius=8+int(18*row.users_affected/actions.users_affected.max()); colour=RED if row.sla_breach_rate>=.3 else AMBER if row.sla_breach_rate>=.2 else TEAL
        draw.ellipse((px-radius,py-radius,px+radius,py+radius),fill=colour,outline=WHITE,width=2); draw.text((px+radius+3,py-6),row.action_id,fill=NAVY,font=pil_font(9,True))
    draw.text((1110,535),"Estimated avoidable staff hours",fill=MUTED,font=pil_font(10)); draw.text((850,390),"Negative experience",fill=MUTED,font=pil_font(10))
    pil_panel(draw, (40, 590, 1560, 860), "Top evidence-backed actions")
    rows=[]
    for row in actions.head(4).itertuples(): rows.append([row.priority,row.issue,f"{row.evidence_1_name}: {row.evidence_1_value:.1%}; n={row.sample_size:,}",row.recommended_action])
    pil_table(draw,(40,590,1560,860),rows,[("Priority",.08),("Issue",.29),("Evidence",.24),("Recommended action",.36)])
    image.save(OUT / "01-executive-operational-health.png")

    image, draw = pil_page("Bottlenecks & Capacity", "Where does work wait, and when will demand exceed productive capacity?")
    stage=query("SELECT s.service_name, AVG(c.assignment_business_hours) assignment FROM fact_case c JOIN dim_service_curated s USING(service_key) GROUP BY 1 ORDER BY assignment DESC")
    pil_panel(draw,(40,110,560,410),"Assignment wait by service"); pil_bar_chart(draw,(40,110,560,410),stage.service_name.tolist(),stage.assignment.tolist(),[RED,AMBER,BLUE])
    work=query("SELECT contractor_name, AVG(on_time_flag) on_time FROM fact_work_order GROUP BY 1 ORDER BY on_time")
    pil_panel(draw,(585,110,1060,410),"Contractor on-time completion"); pil_bar_chart(draw,(585,110,1060,410),work.contractor_name.tolist(),work.on_time.tolist(),[RED,AMBER,TEAL],True)
    open_cases=query("SELECT submitted_datetime FROM fact_case WHERE backlog_eligible_flag=1"); ages=(pd.Timestamp('2026-08-15')-pd.to_datetime(open_cases.submitted_datetime)).dt.days; counts=[int((ages<=7).sum()),int(((ages>7)&(ages<=14)).sum()),int(((ages>14)&(ages<=30)).sum()),int((ages>30).sum())]
    pil_panel(draw,(1085,110,1560,410),"Current backlog age"); pil_bar_chart(draw,(1085,110,1560,410),["0-7 days","8-14 days","15-30 days","30+ days"],counts,[TEAL,BLUE,AMBER,RED])
    cap=query("SELECT week_start,SUM(required_handle_hours) required,SUM(staffed_hours) staffed FROM fact_capacity_weekly GROUP BY 1 ORDER BY 1")
    pil_panel(draw,(40,435,795,860),"Team-level bottlenecks can hide inside aggregate capacity"); pil_line_chart(draw,(40,435,795,860),[cap.required.tolist(),cap.staffed.tolist()],[BLUE,AMBER],["Required hours","Staffed hours"])
    fc=query("SELECT week_start,SUM(predicted_handle_hours) demand,SUM(typical_capacity_hours) capacity FROM fact_demand_forecast WHERE record_type='Forecast' GROUP BY 1 ORDER BY 1")
    pil_panel(draw,(820,435,1560,860),"12-week outlook includes model uncertainty"); pil_line_chart(draw,(820,435,1560,860),[fc.demand.tolist(),fc.capacity.tolist()],[BLUE,AMBER],["Predicted demand","Typical capacity"]); wape=query("SELECT AVG(wape) wape FROM forecast_model_evaluation").iloc[0,0]; draw.text((1435,468),f"Holdout WAPE {wape:.1%}",fill=MUTED,font=pil_font(11),anchor="ra")
    image.save(OUT / "02-bottlenecks-and-capacity.png")

    image, draw = pil_page("Experience & Equity", "Which users experience disproportionate effort, and does operational friction explain the pattern?")
    service_exp=query("SELECT s.service_name,AVG(f.csat_positive_flag) csat,COUNT(*) n FROM fact_feedback f JOIN dim_service_curated s USING(service_key) WHERE feedback_type='Post-case survey' GROUP BY 1 ORDER BY csat")
    pil_panel(draw,(40,110,560,430),"CSAT positive by service"); pil_bar_chart(draw,(40,110,560,430),service_exp.service_name.tolist(),service_exp.csat.tolist(),[RED,AMBER,TEAL],True)
    cohort_cases=query("SELECT cohort_key,COUNT(*) cases FROM fact_case GROUP BY 1"); pop=query("SELECT cohort_key,AVG(users) population FROM (SELECT month_start,cohort_key,SUM(active_users) users FROM fact_population_monthly GROUP BY 1,2) GROUP BY 1"); cohort=cohort_cases.merge(pop,on='cohort_key').merge(query("SELECT cohort_key,cohort_name FROM dim_cohort_curated"),on='cohort_key'); cohort['rate']=cohort.cases/cohort.population*1000; cohort=cohort.sort_values('rate',ascending=False).head(6)
    pil_panel(draw,(585,110,1060,430),"Cases per 1,000 active users"); pil_bar_chart(draw,(585,110,1060,430),cohort.cohort_name.tolist(),cohort.rate.tolist(),[RED]+[BLUE]*5)
    bands=query("SELECT c.resolution_time_band,AVG(f.csat_positive_flag) csat FROM fact_feedback f JOIN fact_case c ON c.case_id=f.related_case_id WHERE f.feedback_type='Post-case survey' GROUP BY 1"); bands=bands[bands.resolution_time_band!='Open/Excluded']; order={'0–8h':0,'9–24h':1,'25–80h':2,'80h+':3}; bands=bands.assign(ord=bands.resolution_time_band.map(order)).sort_values('ord')
    pil_panel(draw,(1085,110,1560,430),"Long waits align with lower CSAT"); pil_bar_chart(draw,(1085,110,1560,430),bands.resolution_time_band.tolist(),bands.csat.tolist(),[TEAL,BLUE,AMBER,RED],True)
    themes=query("SELECT feedback_theme,COUNT(*) n FROM fact_feedback WHERE feedback_type='Post-case survey' GROUP BY 1 ORDER BY n DESC")
    pil_panel(draw,(40,455,790,860),"Feedback volume by theme"); pil_bar_chart(draw,(40,455,790,860),themes.feedback_theme.tolist(),themes.n.tolist(),[BLUE]*len(themes))
    digital=query("SELECT substr(date,1,7) month,service_key,AVG(completion_rate) completion FROM fact_digital_journey_daily GROUP BY 1,2 ORDER BY 1")
    pil_panel(draw,(815,455,1560,860),"Digital completion improved after intervention"); pil_line_chart(draw,(815,455,1560,860),[digital[digital.service_key==1].completion.mul(100).tolist(),digital[digital.service_key==2].completion.mul(100).tolist()],[BLUE,TEAL],["Student Admin","IT Support"])
    image.save(OUT / "03-experience-and-equity.png")

    image, draw = pil_page("Actions & Benefits", "What should change, who owns it, and how will improvement be measured?")
    pil_metrics(draw,[("Actions tracked",str(len(actions)),"evidence-backed","good"),("Completed",str(int((actions.action_status=='Completed').sum())),"benefit measured","good"),("In progress",str(int((actions.action_status=='In progress').sum())),"owner assigned","warn"),("Planned",str(int((actions.action_status=='Planned').sum())),"review scheduled","warn"),("Avoidable effort",f"{actions.estimated_avoidable_staff_hours.sum():,.0f}h","opportunity estimate","bad"),("Users affected",f"{actions.users_affected.sum():,}","not de-duplicated","warn")])
    pil_panel(draw,(40,220,1560,650),"Action register: evidence, accountability and review")
    action_rows=[]
    for row in actions.head(6).itertuples(): action_rows.append([row.priority,row.issue,f"{row.evidence_1_name}: {row.evidence_1_value:.1%}; n={row.sample_size:,}",row.owner,row.action_status,str(row.next_review_date)[:10]])
    pil_table(draw,(40,220,1560,650),action_rows,[("Priority",.07),("Issue",.28),("Evidence",.22),("Owner",.17),("Status",.11),("Review",.11)])
    dq=query("SELECT issue_type,COUNT(*) n FROM data_quality_issues GROUP BY 1 ORDER BY n DESC"); wape=query("SELECT AVG(wape) wape FROM forecast_model_evaluation").iloc[0,0]
    pil_panel(draw,(40,680,1560,860),"Data health and model assurance are visible, not hidden")
    health=[("Data-quality issues",f"{dq.n.sum():,}"),("Largest issue",str(dq.iloc[0].issue_type)),("Forecast holdout WAPE",f"{wape:.1%}"),("Governance status","Reconciled")]
    for i,(label,value) in enumerate(health): x=75+i*375; draw.text((x,730),label,fill=MUTED,font=pil_font(12)); draw.text((x,765),value,fill=TEAL if i==3 else NAVY,font=pil_font(24,True))
    image.save(OUT / "04-actions-and-benefits.png")


def main():
    if HAVE_MATPLOTLIB:
        executive_page(); bottlenecks_page(); experience_page(); actions_page()
    else:
        create_pil_mockups()
    for path in sorted(OUT.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
