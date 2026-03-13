"""
Parallax — Multi-Persona Test Runner
Runs 2-3 personas sequentially to verify different persona behaviors.
This is the Day 1 evening verification script.

Usage:
    python run_multi_test.py --url "https://en.wikipedia.org" --task "Find info about climate change"
    python run_multi_test.py --personas martha,raj,dev --url "https://en.wikipedia.org"
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from personas.definitions import PERSONAS, get_persona_by_name
from run_navigator import NavigatorRunner


async def run_multi_test(persona_names: list[str], url: str, task: str, delay_between: int = 30):
    """Run multiple personas sequentially and compare results."""
    
    print(f"\n{'='*70}")
    print(f"🔬 PARALLAX — Multi-Persona UX Test")
    print(f"{'='*70}")
    print(f"  🌐 URL: {url}")
    print(f"  🎯 Task: {task}")
    print(f"  👥 Personas: {', '.join(persona_names)}")
    print(f"  🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")
    
    results = []
    
    for i, name in enumerate(persona_names, 1):
        try:
            persona = get_persona_by_name(name)
        except ValueError as e:
            print(f"❌ {e}")
            continue
        
        print(f"\n{'─'*70}")
        print(f"  Running persona {i}/{len(persona_names)}: {persona.name}")
        print(f"{'─'*70}")
        
        runner = NavigatorRunner(persona, url, task)
        journey = await runner.run()
        
        results.append({
            "persona": persona.name,
            "age": persona.age,
            "tech_level": persona.tech_level,
            "task_completed": journey.task_completed,
            "gave_up": journey.gave_up,
            "gave_up_reason": journey.gave_up_reason,
            "total_steps": journey.total_steps,
            "max_frustration": journey.max_frustration_reached,
            "key_confusions": journey.key_confusions[:5],
        })
        
        # Cooldown between personas to avoid rate limits
        if i < len(persona_names) and delay_between > 0:
            print(f"\n  ⏳ Cooling down {delay_between}s before next persona (avoiding API rate limits)...")
            for remaining in range(delay_between, 0, -10):
                print(f"     {remaining}s remaining...", end="\r")
                await asyncio.sleep(min(10, remaining))
            print(f"     Ready!{'':20}")
    
    # Print comparison
    print(f"\n{'='*70}")
    print(f"📊 COMPARISON RESULTS")
    print(f"{'='*70}\n")
    
    print(f"{'Persona':<12} {'Age':<5} {'Tech':<5} {'Steps':<7} {'Frust.':<8} {'Result':<15}")
    print(f"{'─'*60}")
    
    for r in results:
        status = "✅ Completed" if r["task_completed"] else "❌ Gave up"
        print(f"{r['persona']:<12} {r['age']:<5} {r['tech_level']:<5} {r['total_steps']:<7} {r['max_frustration']:<8} {status}")
    
    print(f"\n{'─'*60}")
    
    # Highlight differences
    completers = [r["persona"] for r in results if r["task_completed"]]
    quitters = [r["persona"] for r in results if r["gave_up"]]
    
    if completers:
        print(f"\n  ✅ Completed: {', '.join(completers)}")
    if quitters:
        print(f"  ❌ Gave up: {', '.join(quitters)}")
        for r in results:
            if r["gave_up"] and r["gave_up_reason"]:
                print(f"     • {r['persona']}: {r['gave_up_reason']}")
    
    # Unique confusions per persona
    print(f"\n  🔍 Key Confusions by Persona:")
    for r in results:
        if r["key_confusions"]:
            print(f"     {r['persona']}:")
            for c in r["key_confusions"][:3]:
                print(f"       - {c}")
    
    print(f"\n{'='*70}")
    print(f"  Test complete! {len(results)} personas tested.")
    print(f"{'='*70}\n")
    
    # Save comparison report
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump({
            "url": url,
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }, f, indent=2)
    print(f"  💾 Comparison saved to: {report_path}")
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="Parallax — Multi-Persona UX Test")
    parser.add_argument("--personas", "-p", type=str, default="martha,raj,dev",
                       help="Comma-separated persona names")
    parser.add_argument("--url", "-u", type=str, default="https://en.wikipedia.org",
                       help="Target URL to test")
    parser.add_argument("--task", "-t", type=str, 
                       default="Find information about climate change and navigate to a related topic",
                       help="Task for personas to complete")
    
    parser.add_argument("--delay", "-d", type=int, default=30,
                       help="Seconds to wait between personas (default 30, avoids rate limits)")
    
    args = parser.parse_args()
    persona_names = [n.strip() for n in args.personas.split(",")]
    
    await run_multi_test(persona_names, args.url, args.task, args.delay)


if __name__ == "__main__":
    asyncio.run(main())
