"""
Parallax — Analyst Agent
Uses Gemini to analyze journey data from all persona navigators and 
identify cross-persona UX patterns, severity, and recommendations.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent


# ============================================================
# Analyst Tool Functions
# ============================================================

async def analyze_journeys(journey_data: str) -> dict:
    """
    Analyze journey data from multiple personas.
    This tool receives raw journey JSON strings from navigator agents 
    and processes them into structured findings.
    
    Args:
        journey_data: JSON string containing all persona journey results
    
    Returns:
        Structured analysis with patterns, issues, and recommendations.
    """
    try:
        journeys = json.loads(journey_data) if isinstance(journey_data, str) else journey_data
    except json.JSONDecodeError:
        return {"status": "error", "message": "Could not parse journey data"}
    
    if not isinstance(journeys, list):
        journeys = [journeys]
    
    # Extract cross-persona metrics
    total_personas = len(journeys)
    completed = [j for j in journeys if j.get("success")]
    gave_up = [j for j in journeys if not j.get("success")]
    
    # Collect all confusions
    all_confusions = []
    for j in journeys:
        persona = j.get("persona", "Unknown")
        for c in j.get("key_confusions", []):
            all_confusions.append({"persona": persona, "confusion": c})
    
    # Calculate completion rate
    completion_rate = len(completed) / total_personas * 100 if total_personas > 0 else 0
    
    # Average frustration
    frustrations = [j.get("frustration", 0) for j in journeys]
    avg_frustration = sum(frustrations) / len(frustrations) if frustrations else 0
    
    # Average steps
    steps = [j.get("total_steps", j.get("steps_taken", 0)) for j in journeys]
    avg_steps = sum(steps) / len(steps) if steps else 0
    
    return {
        "status": "analyzed",
        "metrics": {
            "total_personas": total_personas,
            "completed": len(completed),
            "gave_up": len(gave_up),
            "completion_rate": f"{completion_rate:.0f}%",
            "avg_frustration": round(avg_frustration, 1),
            "avg_steps": round(avg_steps, 1),
        },
        "who_completed": [j.get("persona") for j in completed],
        "who_gave_up": [
            {"persona": j.get("persona"), "reason": j.get("summary", "Unknown")}
            for j in gave_up
        ],
        "all_confusions": all_confusions,
        "raw_journeys": journeys,
    }


async def generate_ux_report(analysis_json: str) -> dict:
    """
    Generate a structured UX report from analysis results.
    The agent will use this data along with its reasoning to create 
    the final prioritized report.
    
    Args:
        analysis_json: JSON string of analysis results from analyze_journeys
    
    Returns:
        Report structure ready for the agent to fill in with insights.
    """
    try:
        analysis = json.loads(analysis_json) if isinstance(analysis_json, str) else analysis_json
    except json.JSONDecodeError:
        return {"status": "error", "message": "Could not parse analysis data"}
    
    metrics = analysis.get("metrics", {})
    
    return {
        "status": "report_ready",
        "report_template": {
            "title": "Parallax UX Analysis Report",
            "summary_metrics": metrics,
            "sections": [
                "Executive Summary",
                "Cross-Persona Patterns",
                "Individual Persona Journeys",
                "Prioritized Issues",
                "Recommendations",
            ],
        },
        "instructions": (
            "Use the analysis data to fill in each report section. "
            "Focus on: (1) issues that affected MULTIPLE personas, "
            "(2) accessibility barriers, (3) cognitive load problems, "
            "(4) specific actionable recommendations with severity ratings."
        ),
    }


# ============================================================
# Analyst Agent Factory
# ============================================================

def create_analyst_agent() -> Agent:
    """
    Create the Analyst ADK Agent.
    This agent receives journey data from all navigators and produces
    a prioritized UX report with cross-persona pattern analysis.
    """
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    instruction = """You are the Parallax UX Analyst Agent. Your job is to analyze 
the journey data from multiple persona navigators and produce a comprehensive UX report.

WHAT YOU RECEIVE:
You will have access to journey results from multiple persona agents via shared state.
Each journey contains: persona name, success/failure, frustration level, steps taken,
key confusions, and UX issues encountered.

YOUR ANALYSIS PROCESS:
1. First, call analyze_journeys() with the journey data to extract metrics.
2. Look for CROSS-PERSONA PATTERNS:
   - If 3+ personas struggled with the same element → CRITICAL issue
   - If 2 personas had the same confusion → HIGH priority issue
   - If only 1 persona struggled → could be persona-specific or MEDIUM issue
3. Pay special attention to:
   - Accessibility issues (Sam's screen reader experience)
   - Language barriers (Yuki's ESL challenges)
   - Age-related difficulties (Martha's tech challenges)
   - Visual design issues (Dev's expectations, Carlos's colorblindness)
4. Call generate_ux_report() with your analysis to structure the report.
5. Output a final prioritized list of findings with:
   - Issue title and description
   - Severity (critical/high/medium/low)
   - Which personas were affected
   - Specific recommendation to fix it

IMPORTANT: Focus on ACTIONABLE insights. Don't just list problems — recommend solutions.
Every finding must reference which specific personas experienced it and why.

Output your final analysis as structured text that can be displayed in a dashboard."""

    return Agent(
        name="ux_analyst",
        model=model,
        description=(
            "Analyzes journey data from all persona navigators. "
            "Identifies cross-persona UX patterns and generates "
            "a prioritized report with actionable recommendations."
        ),
        instruction=instruction,
        output_key="ux_report",
        tools=[
            analyze_journeys,
            generate_ux_report,
        ],
    )
