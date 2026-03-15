"""
Parallax — Orchestrator Agent
The root agent that orchestrates the full UX testing pipeline:
  1. Run navigator agents (sequentially with rate-limit delays) 
  2. Collect journey results
  3. Run the analyst agent to generate the UX report

Uses ADK SequentialAgent to chain navigation → analysis phases.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents import Agent, SequentialAgent

from personas.definitions import PERSONAS, get_persona_by_name, Persona
from agents.navigator import create_navigator_agent
from agents.analyst import create_analyst_agent


def create_orchestrator(
    target_url: str,
    task: str,
    persona_names: list[str] | None = None,
) -> SequentialAgent:
    """
    Create the Parallax orchestrator agent.
    
    Architecture:
        SequentialAgent (orchestrator)
        ├── Navigator_Martha (Agent with browser tools)
        ├── Navigator_Raj (Agent with browser tools)
        ├── Navigator_Dev (Agent with browser tools)
        ├── ... (one per selected persona)
        └── UX_Analyst (Agent that analyzes all journey results)
    
    Note: We run navigators sequentially (not parallel) because:
    1. API rate limits on free tier (10 RPM for gemini-2.5-flash)
    2. Each navigator needs its own browser instance
    3. Sequential is more reliable for demos
    
    Args:
        target_url: Website URL to test
        task: Task description for personas
        persona_names: List of persona names to use, or None for all 7
    
    Returns:
        Configured SequentialAgent orchestrator
    """
    # Select personas
    if persona_names:
        personas = []
        for name in persona_names:
            try:
                personas.append(get_persona_by_name(name))
            except ValueError:
                print(f"⚠️ Unknown persona: {name}, skipping")
    else:
        personas = PERSONAS
    
    # Create navigator agents for each persona
    navigator_agents = [
        create_navigator_agent(persona, target_url, task)
        for persona in personas
    ]
    
    # Create the analyst agent
    analyst = create_analyst_agent()
    
    # Build the sequential pipeline: navigators first, then analyst
    all_sub_agents = navigator_agents + [analyst]
    
    orchestrator = SequentialAgent(
        name="parallax_orchestrator",
        description=(
            f"Parallax UX Testing Orchestrator. "
            f"Tests {target_url} with {len(personas)} diverse personas, "
            f"then analyzes results for cross-persona UX patterns. "
            f"Personas: {', '.join(p.name for p in personas)}."
        ),
        sub_agents=all_sub_agents,
    )
    
    return orchestrator


# ============================================================
# Standalone pipeline runner (bypasses ADK runtime)
# ============================================================

async def run_pipeline(
    target_url: str,
    task: str,
    persona_names: list[str] | None = None,
    delay_between: int = 30,
    run_id: str | None = None,
) -> dict:
    """
    Run the full Parallax pipeline outside of ADK runtime.
    This is more practical for development since it:
    - Handles rate limiting with delays
    - Saves screenshots and journey data
    - Provides real-time console output
    
    For the ADK-native version, use create_orchestrator() with adk run/web.
    
    Args:
        target_url: Website to test
        task: Task for personas
        persona_names: Which personas to run (default: all 7)
        delay_between: Seconds between personas (rate limit protection)
    
    Returns:
        Full pipeline results dict
    """
    import asyncio
    import json
    from datetime import datetime
    from pathlib import Path
    from run_navigator import NavigatorRunner
    
    if persona_names is None:
        persona_names = [p.name.lower() for p in PERSONAS]
    
    print(f"\n{'='*70}")
    print(f"🔬 PARALLAX — Full Pipeline")
    print(f"{'='*70}")
    print(f"  🌐 URL: {target_url}")
    print(f"  🎯 Task: {task}")
    print(f"  👥 Personas: {', '.join(persona_names)}")
    print(f"  ⏱️  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    # Phase 1: Run navigators
    print(f"\n{'─'*70}")
    print(f"  📡 PHASE 1: Running {len(persona_names)} persona navigators")
    print(f"{'─'*70}\n")
    
    journey_results = []
    
    for i, name in enumerate(persona_names, 1):
        try:
            persona = get_persona_by_name(name)
        except ValueError:
            print(f"  ⚠️ Unknown persona: {name}, skipping")
            continue
        
        print(f"\n  [{i}/{len(persona_names)}] Running {persona.name}...")
        
        runner = NavigatorRunner(persona, target_url, task, run_id=run_id)
        journey = await runner.run()
        
        result = {
            "persona": persona.name,
            "age": persona.age,
            "tech_level": persona.tech_level,
            "background": persona.background,
            "success": journey.task_completed,
            "summary": journey.gave_up_reason or "Task completed",
            "frustration": journey.max_frustration_reached,
            "total_steps": journey.total_steps,
            "key_confusions": journey.key_confusions[:5],
            "ux_issues_found": len([
                s for s in journey.steps if s.confusion_points
            ]),
        }
        journey_results.append(result)
        
        # Cooldown between personas
        if i < len(persona_names) and delay_between > 0:
            print(f"\n  ⏳ Cooling down {delay_between}s...")
            await asyncio.sleep(delay_between)
    
    # Phase 2: Run Analyst
    print(f"\n{'─'*70}")
    print(f"  🔍 PHASE 2: Analyzing cross-persona patterns")
    print(f"{'─'*70}\n")
    
    from agents.analyst import analyze_journeys, generate_ux_report
    
    analysis = await analyze_journeys(json.dumps(journey_results))
    report_data = await generate_ux_report(json.dumps(analysis))
    
    # Generate AI-powered analysis
    from google import genai
    from google.genai import types as genai_types
    from dotenv import load_dotenv
    load_dotenv()
    
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    analysis_prompt = f"""You are the Parallax UX Analyst. Analyze these journey results 
from {len(journey_results)} diverse user personas testing {target_url}.

JOURNEY DATA:
{json.dumps(journey_results, indent=2)}

METRICS:
{json.dumps(analysis.get('metrics', {}), indent=2)}

Generate a concise UX report with:
1. EXECUTIVE SUMMARY (2-3 sentences)
2. CROSS-PERSONA PATTERNS (issues that affected multiple personas)
3. PRIORITIZED ISSUES (severity + which personas + recommendation)
4. ACCESSIBILITY FINDINGS (if any)
5. TOP 3 RECOMMENDATIONS

Keep it actionable and specific. Reference persona names and their behaviors."""

    try:
        response = client.models.generate_content(
            model=model,
            contents=[genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=analysis_prompt)],
            )],
            config=genai_types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2000,
            ),
        )
        ai_report = response.text.strip()
    except Exception as e:
        ai_report = f"[Could not generate AI analysis: {e}]"
    
    # Print report
    print(f"\n{'='*70}")
    print(f"📊 PARALLAX UX REPORT")
    print(f"{'='*70}")
    print(f"\n{ai_report}")
    print(f"\n{'='*70}")
    
    # Print summary table
    print(f"\n📈 PERSONA COMPARISON:")
    print(f"{'─'*60}")
    print(f"{'Persona':<12} {'Age':<5} {'Tech':<5} {'Steps':<7} {'Frust.':<8} {'Result'}")
    print(f"{'─'*60}")
    for r in journey_results:
        status = "✅" if r["success"] else "❌"
        print(f"{r['persona']:<12} {r['age']:<5} {r['tech_level']:<5} "
              f"{r['total_steps']:<7} {r['frustration']:<8} {status}")
    print(f"{'─'*60}\n")
    
    # Save everything
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_tag = f"{run_id}_{timestamp}" if run_id else timestamp
    report_path = output_dir / f"pipeline_report_{report_tag}.json"
    
    full_report = {
        "url": target_url,
        "task": task,
        "timestamp": datetime.now().isoformat(),
        "metrics": analysis.get("metrics", {}),
        "persona_results": journey_results,
        "ai_report": ai_report,
    }
    
    with open(report_path, "w") as f:
        json.dump(full_report, f, indent=2)
    
    # Also save the text report
    text_path = output_dir / f"ux_report_{report_tag}.md"
    with open(text_path, "w") as f:
        f.write(f"# Parallax UX Report\n\n")
        f.write(f"**URL:** {target_url}\n")
        f.write(f"**Task:** {task}\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Personas tested:** {len(journey_results)}\n\n")
        f.write(f"---\n\n")
        f.write(ai_report)
        f.write(f"\n\n---\n\n## Raw Metrics\n\n")
        f.write(f"| Persona | Age | Tech | Steps | Frustration | Result |\n")
        f.write(f"|---------|-----|------|-------|-------------|--------|\n")
        for r in journey_results:
            status = "✅ Complete" if r["success"] else "❌ Gave up"
            f.write(f"| {r['persona']} | {r['age']} | {r['tech_level']} | "
                    f"{r['total_steps']} | {r['frustration']} | {status} |\n")
    
    print(f"  💾 Report saved to: {report_path}")
    print(f"  📝 Markdown report: {text_path}")
    print(f"  ✅ Pipeline complete!\n")
    
    return full_report
