#!/usr/bin/env python3
"""
CRM AI MCP Server
=====================
Customer relationship management toolkit for AI agents: lead scoring,
deal stage prediction, follow-up scheduling, customer health scoring,
and churn prediction.

By MEOK AI Labs | https://meok.ai

Install: pip install mcp
Run:     python server.py
"""


import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 30
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade: https://mcpize.com/crm-ai-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------
def _lead_score(company_size: int, industry: str, budget: float,
                engagement_signals: dict, source: str,
                days_since_first_touch: int) -> dict:
    """Score a lead based on firmographic and behavioral data."""
    score = 0
    breakdown = {}

    # Company size scoring (0-20)
    if company_size >= 1000:
        size_score = 20
    elif company_size >= 250:
        size_score = 16
    elif company_size >= 50:
        size_score = 12
    elif company_size >= 10:
        size_score = 8
    else:
        size_score = 4
    score += size_score
    breakdown["company_size"] = size_score

    # Industry fit (0-15)
    high_value_industries = {"technology", "finance", "healthcare", "saas", "ecommerce"}
    medium_value = {"manufacturing", "retail", "education", "consulting", "real_estate"}
    if industry.lower() in high_value_industries:
        ind_score = 15
    elif industry.lower() in medium_value:
        ind_score = 10
    else:
        ind_score = 5
    score += ind_score
    breakdown["industry"] = ind_score

    # Budget (0-20)
    if budget >= 100000:
        budget_score = 20
    elif budget >= 50000:
        budget_score = 16
    elif budget >= 10000:
        budget_score = 12
    elif budget >= 1000:
        budget_score = 8
    else:
        budget_score = 4
    score += budget_score
    breakdown["budget"] = budget_score

    # Engagement signals (0-30)
    engagement_score = 0
    signal_weights = {
        "website_visits": 2, "email_opens": 1, "email_clicks": 3,
        "demo_requested": 10, "content_downloads": 3, "pricing_page_views": 5,
        "webinar_attended": 4, "form_submitted": 5, "chat_initiated": 4,
    }
    engagement_details = {}
    for signal, count in engagement_signals.items():
        weight = signal_weights.get(signal, 1)
        points = min(count * weight, 10)
        engagement_score += points
        engagement_details[signal] = {"count": count, "points": points}
    engagement_score = min(30, engagement_score)
    score += engagement_score
    breakdown["engagement"] = engagement_score

    # Source quality (0-10)
    source_scores = {
        "referral": 10, "organic_search": 8, "direct": 7,
        "linkedin": 6, "webinar": 7, "content": 5,
        "paid_search": 4, "paid_social": 3, "cold_outreach": 2,
    }
    src_score = source_scores.get(source.lower(), 3)
    score += src_score
    breakdown["source"] = src_score

    # Recency decay (0-5)
    if days_since_first_touch <= 7:
        recency = 5
    elif days_since_first_touch <= 30:
        recency = 4
    elif days_since_first_touch <= 90:
        recency = 3
    else:
        recency = max(0, 5 - days_since_first_touch // 90)
    score += recency
    breakdown["recency"] = recency

    total = min(100, score)

    if total >= 80:
        tier = "Hot"
        action = "Immediate sales outreach. High-priority lead."
    elif total >= 60:
        tier = "Warm"
        action = "Schedule discovery call within 48 hours."
    elif total >= 40:
        tier = "Nurture"
        action = "Add to nurture sequence. Send targeted content."
    else:
        tier = "Cold"
        action = "Low priority. Monitor for engagement increases."

    return {
        "score": total,
        "tier": tier,
        "recommended_action": action,
        "breakdown": breakdown,
        "engagement_details": engagement_details,
        "conversion_probability_pct": round(min(95, total * 0.8 + 5), 1),
    }


def _deal_stage_predictor(deal_value: float, days_in_pipeline: int,
                          current_stage: str, activities_count: int,
                          competitor_mentioned: bool,
                          champion_identified: bool) -> dict:
    """Predict deal progression and win probability."""
    stages = {
        "prospecting": {"order": 1, "base_prob": 10, "avg_days": 14},
        "qualification": {"order": 2, "base_prob": 20, "avg_days": 21},
        "discovery": {"order": 3, "base_prob": 35, "avg_days": 14},
        "proposal": {"order": 4, "base_prob": 55, "avg_days": 21},
        "negotiation": {"order": 5, "base_prob": 70, "avg_days": 14},
        "closed_won": {"order": 6, "base_prob": 100, "avg_days": 0},
        "closed_lost": {"order": 7, "base_prob": 0, "avg_days": 0},
    }

    stage_lower = current_stage.lower().replace(" ", "_")
    if stage_lower not in stages:
        return {"error": f"Unknown stage '{current_stage}'. Use: {list(stages.keys())}"}

    stage_info = stages[stage_lower]
    base_prob = stage_info["base_prob"]

    # Adjustments
    adjustments = {}

    # Activity level
    if activities_count >= 10:
        adj = 10
    elif activities_count >= 5:
        adj = 5
    else:
        adj = -5
    adjustments["activity_level"] = adj

    # Deal velocity (time in pipeline)
    expected_days = sum(s["avg_days"] for s in stages.values() if s["order"] <= stage_info["order"])
    if days_in_pipeline <= expected_days:
        vel_adj = 5
    elif days_in_pipeline > expected_days * 2:
        vel_adj = -15
    else:
        vel_adj = -5
    adjustments["velocity"] = vel_adj

    # Champion
    if champion_identified:
        adjustments["champion"] = 10
    else:
        adjustments["no_champion"] = -10 if stage_info["order"] >= 3 else 0

    # Competition
    if competitor_mentioned:
        adjustments["competition"] = -10
    else:
        adjustments["no_competition"] = 5

    # Deal size factor
    if deal_value > 100000:
        adjustments["enterprise_deal"] = -5  # Larger deals are harder
    elif deal_value < 5000:
        adjustments["small_deal"] = 5

    total_adj = sum(adjustments.values())
    win_probability = max(1, min(95, base_prob + total_adj))

    # Next stage prediction
    next_stages = {k: v for k, v in stages.items() if v["order"] == stage_info["order"] + 1}
    next_stage = list(next_stages.keys())[0] if next_stages else "closed_won"

    # Expected close date
    remaining_days = sum(s["avg_days"] for s in stages.values() if s["order"] > stage_info["order"] and s["order"] < 6)

    return {
        "current_stage": current_stage,
        "win_probability_pct": round(win_probability, 1),
        "deal_value": deal_value,
        "weighted_value": round(deal_value * (win_probability / 100), 2),
        "next_stage": next_stage,
        "estimated_days_to_close": remaining_days,
        "estimated_close_date": (datetime.now() + timedelta(days=remaining_days)).strftime("%Y-%m-%d"),
        "days_in_pipeline": days_in_pipeline,
        "adjustments": adjustments,
        "risk_factors": [k for k, v in adjustments.items() if v < 0],
        "positive_factors": [k for k, v in adjustments.items() if v > 0],
        "recommendation": (
            "Strong deal - push for close" if win_probability > 70 else
            "On track - maintain momentum" if win_probability > 50 else
            "At risk - schedule urgent review" if win_probability > 30 else
            "Low probability - consider deprioritizing"
        ),
    }


def _followup_scheduler(contacts: list[dict], strategy: str) -> dict:
    """Schedule follow-ups based on contact engagement and priority."""
    if not contacts:
        return {"error": "Provide contacts as [{name, email, last_contact_date, priority, deal_value}]"}

    strategies = {
        "aggressive": {"high": 2, "medium": 5, "low": 10},
        "standard": {"high": 5, "medium": 10, "low": 21},
        "nurture": {"high": 7, "medium": 14, "low": 30},
        "reactivation": {"high": 3, "medium": 7, "low": 14},
    }

    if strategy not in strategies:
        return {"error": f"Unknown strategy. Use: {list(strategies.keys())}"}

    intervals = strategies[strategy]
    now = datetime.now()
    schedule = []

    for contact in contacts:
        name = contact.get("name", "Unknown")
        priority = contact.get("priority", "medium").lower()
        deal_value = contact.get("deal_value", 0)

        try:
            last_contact = datetime.strptime(contact.get("last_contact_date", ""), "%Y-%m-%d")
        except ValueError:
            last_contact = now - timedelta(days=30)

        days_since = (now - last_contact).days
        interval = intervals.get(priority, 10)

        next_followup = last_contact + timedelta(days=interval)
        if next_followup < now:
            next_followup = now + timedelta(days=1)
            overdue = True
        else:
            overdue = False

        # Determine channel
        if days_since > 30:
            channel = "phone_call"
            message_type = "Re-engagement"
        elif priority == "high":
            channel = "phone_call"
            message_type = "Check-in"
        elif days_since > 14:
            channel = "email"
            message_type = "Value-add content"
        else:
            channel = "email"
            message_type = "Quick update"

        schedule.append({
            "name": name,
            "email": contact.get("email", ""),
            "priority": priority,
            "deal_value": deal_value,
            "last_contact": last_contact.strftime("%Y-%m-%d"),
            "days_since_contact": days_since,
            "next_followup": next_followup.strftime("%Y-%m-%d"),
            "overdue": overdue,
            "channel": channel,
            "message_type": message_type,
        })

    schedule.sort(key=lambda x: (not x["overdue"], x["next_followup"]))
    overdue_count = sum(1 for s in schedule if s["overdue"])

    return {
        "strategy": strategy,
        "contact_count": len(schedule),
        "overdue_count": overdue_count,
        "schedule": schedule,
        "this_week": [s for s in schedule if datetime.strptime(s["next_followup"], "%Y-%m-%d") <= now + timedelta(days=7)],
        "summary": f"{overdue_count} overdue, {len(schedule) - overdue_count} scheduled on time",
    }


def _customer_health_score(usage_metrics: dict, support_tickets: int,
                           nps_score: int, contract_value: float,
                           months_as_customer: int,
                           feature_adoption_pct: float) -> dict:
    """Calculate customer health score from multiple signals."""
    score = 0
    breakdown = {}

    # Usage (0-30)
    logins = usage_metrics.get("monthly_logins", 0)
    active_users = usage_metrics.get("active_users", 0)
    total_users = usage_metrics.get("total_users", 1)
    usage_rate = (active_users / max(total_users, 1)) * 100

    if usage_rate >= 80:
        usage_score = 30
    elif usage_rate >= 60:
        usage_score = 22
    elif usage_rate >= 40:
        usage_score = 15
    elif usage_rate >= 20:
        usage_score = 8
    else:
        usage_score = 3
    score += usage_score
    breakdown["usage"] = {"score": usage_score, "active_rate_pct": round(usage_rate, 1)}

    # Support (0-20) - fewer tickets = healthier
    if support_tickets == 0:
        support_score = 20
    elif support_tickets <= 2:
        support_score = 15
    elif support_tickets <= 5:
        support_score = 10
    elif support_tickets <= 10:
        support_score = 5
    else:
        support_score = 0
    score += support_score
    breakdown["support"] = {"score": support_score, "tickets": support_tickets}

    # NPS (0-20)
    if nps_score >= 9:
        nps_points = 20
        nps_category = "Promoter"
    elif nps_score >= 7:
        nps_points = 12
        nps_category = "Passive"
    else:
        nps_points = 4
        nps_category = "Detractor"
    score += nps_points
    breakdown["nps"] = {"score": nps_points, "nps": nps_score, "category": nps_category}

    # Feature adoption (0-15)
    adoption_score = min(15, int(feature_adoption_pct / 100 * 15))
    score += adoption_score
    breakdown["feature_adoption"] = {"score": adoption_score, "adoption_pct": feature_adoption_pct}

    # Tenure (0-15)
    if months_as_customer >= 24:
        tenure_score = 15
    elif months_as_customer >= 12:
        tenure_score = 12
    elif months_as_customer >= 6:
        tenure_score = 8
    else:
        tenure_score = 4
    score += tenure_score
    breakdown["tenure"] = {"score": tenure_score, "months": months_as_customer}

    total = min(100, score)

    if total >= 80:
        health = "Healthy"
        color = "green"
        action = "Upsell opportunity. Schedule expansion conversation."
    elif total >= 60:
        health = "Stable"
        color = "yellow"
        action = "Monitor closely. Increase engagement touchpoints."
    elif total >= 40:
        health = "At Risk"
        color = "orange"
        action = "Immediate intervention needed. Schedule executive business review."
    else:
        health = "Critical"
        color = "red"
        action = "Escalate to CS leadership. Risk of churn within 90 days."

    return {
        "health_score": total,
        "health_status": health,
        "color": color,
        "recommended_action": action,
        "contract_value": contract_value,
        "arr_at_risk": round(contract_value * (1 - total / 100), 2),
        "breakdown": breakdown,
    }


def _churn_predictor(months_as_customer: int, monthly_usage_trend: list[float],
                     support_tickets_last_90d: int, nps_score: int,
                     contract_renewal_days: int, competitor_mentions: int) -> dict:
    """Predict churn probability based on customer signals."""
    risk_score = 0
    risk_factors = []

    # Usage trend (biggest predictor)
    if len(monthly_usage_trend) >= 3:
        recent = monthly_usage_trend[-1]
        previous = monthly_usage_trend[-3] if len(monthly_usage_trend) >= 3 else monthly_usage_trend[0]
        if previous > 0:
            trend_change = ((recent - previous) / previous) * 100
        else:
            trend_change = 0

        if trend_change < -30:
            risk_score += 30
            risk_factors.append(f"Usage dropped {abs(round(trend_change))}% over last 3 months")
        elif trend_change < -15:
            risk_score += 20
            risk_factors.append(f"Usage declining ({round(trend_change)}%)")
        elif trend_change < 0:
            risk_score += 10
            risk_factors.append("Slight usage decline")
    else:
        trend_change = 0

    # Support tickets
    if support_tickets_last_90d > 10:
        risk_score += 20
        risk_factors.append(f"High support volume ({support_tickets_last_90d} tickets)")
    elif support_tickets_last_90d > 5:
        risk_score += 10
        risk_factors.append("Elevated support tickets")

    # NPS
    if nps_score <= 5:
        risk_score += 20
        risk_factors.append(f"Detractor NPS score ({nps_score})")
    elif nps_score <= 7:
        risk_score += 8
        risk_factors.append("Passive NPS score")

    # Contract renewal proximity
    if contract_renewal_days <= 30:
        risk_score += 10
        risk_factors.append("Contract renewal within 30 days")
    elif contract_renewal_days <= 90:
        risk_score += 5
        risk_factors.append("Contract renewal approaching")

    # Competitor activity
    if competitor_mentions > 0:
        risk_score += min(15, competitor_mentions * 5)
        risk_factors.append(f"Competitor mentioned {competitor_mentions} time(s)")

    # Tenure (newer customers churn more)
    if months_as_customer < 6:
        risk_score += 10
        risk_factors.append("New customer (< 6 months)")

    churn_probability = min(95, max(5, risk_score))

    if churn_probability >= 70:
        urgency = "CRITICAL"
        playbook = "Executive escalation, emergency business review, custom retention offer"
    elif churn_probability >= 50:
        urgency = "HIGH"
        playbook = "CS manager outreach, product training session, success plan review"
    elif churn_probability >= 30:
        urgency = "MEDIUM"
        playbook = "Proactive check-in, share ROI report, invite to user group"
    else:
        urgency = "LOW"
        playbook = "Standard engagement cadence, nurture content"

    return {
        "churn_probability_pct": churn_probability,
        "urgency": urgency,
        "risk_factors": risk_factors,
        "risk_factor_count": len(risk_factors),
        "retention_playbook": playbook,
        "usage_trend_pct": round(trend_change, 1),
        "contract_renewal_days": contract_renewal_days,
        "recommended_actions": [
            "Review product usage analytics in detail",
            "Schedule call with customer champion",
            "Prepare custom ROI analysis",
            f"{'Prepare retention offer' if churn_probability > 50 else 'Continue monitoring'}",
        ],
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CRM AI MCP",
    instructions="Customer relationship management toolkit: lead scoring, deal stage prediction, follow-up scheduling, customer health scoring, and churn prediction. By MEOK AI Labs.")


@mcp.tool()
def lead_scorer(company_size: int, industry: str, budget: float = 0,
                engagement_signals: dict = {}, source: str = "organic_search",
                days_since_first_touch: int = 7, api_key: str = "") -> dict:
    """Score a sales lead (0-100) based on firmographic data, engagement signals,
    and source quality. Returns tier, recommended action, and score breakdown.

    Args:
        company_size: Number of employees
        industry: Industry vertical (e.g. "technology", "finance", "healthcare")
        budget: Estimated budget in dollars
        engagement_signals: Behavioral data as {signal: count} (e.g. {"demo_requested": 1, "email_clicks": 5})
        source: Lead source (referral, organic_search, paid_search, linkedin, etc.)
        days_since_first_touch: Days since first interaction
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _lead_score(company_size, industry, budget, engagement_signals, source, days_since_first_touch)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def deal_stage_predictor(deal_value: float, days_in_pipeline: int = 0,
                         current_stage: str = "qualification",
                         activities_count: int = 0,
                         competitor_mentioned: bool = False,
                         champion_identified: bool = False, api_key: str = "") -> dict:
    """Predict deal win probability and estimated close date based on
    pipeline stage, velocity, and deal characteristics.

    Args:
        deal_value: Deal amount in dollars
        days_in_pipeline: Days since deal was created
        current_stage: Pipeline stage (prospecting, qualification, discovery, proposal, negotiation)
        activities_count: Number of logged activities (calls, emails, meetings)
        competitor_mentioned: Whether a competitor has been mentioned
        champion_identified: Whether an internal champion has been identified
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _deal_stage_predictor(deal_value, days_in_pipeline, current_stage, activities_count, competitor_mentioned, champion_identified)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def followup_scheduler(contacts: list[dict], strategy: str = "standard", api_key: str = "") -> dict:
    """Schedule follow-ups for a list of contacts based on priority,
    last contact date, and engagement strategy.

    Args:
        contacts: List as [{"name": "X", "email": "x@y.com", "last_contact_date": "2026-01-01", "priority": "high", "deal_value": 50000}]
        strategy: Follow-up cadence (aggressive, standard, nurture, reactivation)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _followup_scheduler(contacts, strategy)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def customer_health_score(usage_metrics: dict = {}, support_tickets: int = 0,
                          nps_score: int = 8, contract_value: float = 0,
                          months_as_customer: int = 12,
                          feature_adoption_pct: float = 50.0, api_key: str = "") -> dict:
    """Calculate a customer health score (0-100) from usage, support, NPS,
    adoption, and tenure signals.

    Args:
        usage_metrics: Usage data as {"monthly_logins": N, "active_users": N, "total_users": N}
        support_tickets: Open support tickets in last 30 days
        nps_score: Net Promoter Score (0-10)
        contract_value: Annual contract value
        months_as_customer: Customer tenure in months
        feature_adoption_pct: Percentage of features adopted (0-100)
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _customer_health_score(usage_metrics, support_tickets, nps_score, contract_value, months_as_customer, feature_adoption_pct)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def churn_predictor(months_as_customer: int = 12,
                    monthly_usage_trend: list[float] = [],
                    support_tickets_last_90d: int = 0,
                    nps_score: int = 8,
                    contract_renewal_days: int = 180,
                    competitor_mentions: int = 0, api_key: str = "") -> dict:
    """Predict churn probability and recommend a retention playbook based on
    usage trends, support patterns, and contract timeline.

    Args:
        months_as_customer: Customer tenure in months
        monthly_usage_trend: Recent monthly usage values (e.g. [100, 95, 80, 60])
        support_tickets_last_90d: Support tickets opened in last 90 days
        nps_score: Latest NPS score (0-10)
        contract_renewal_days: Days until contract renewal
        competitor_mentions: Times competitor was mentioned in interactions
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    try:
        return _churn_predictor(months_as_customer, monthly_usage_trend, support_tickets_last_90d, nps_score, contract_renewal_days, competitor_mentions)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
