"""
Parallax — Full Pipeline Runner
Runs the complete Parallax UX testing pipeline:
  Phase 1: Multiple persona navigators browse the target website
  Phase 2: Analyst agent generates cross-persona UX report

Usage:
    python run_pipeline.py --url "https://en.wikipedia.org" --task "Find info about climate change"
    python run_pipeline.py --personas martha,raj,dev --url "https://healthcare.gov"
    python run_pipeline.py --all --url "https://en.wikipedia.org"  # All 7 personas
"""

import asyncio
import argparse

from dotenv import load_dotenv
load_dotenv()

from agents.orchestrator import run_pipeline


async def main():
    parser = argparse.ArgumentParser(description="Parallax — Full UX Testing Pipeline")
    parser.add_argument("--url", "-u", type=str, default="https://en.wikipedia.org",
                       help="Target URL to test")
    parser.add_argument("--task", "-t", type=str,
                       default="Find information about climate change and navigate to a related topic",
                       help="Task for personas to complete")
    parser.add_argument("--personas", "-p", type=str, default="martha,raj,dev",
                       help="Comma-separated persona names")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Run all 7 personas")
    parser.add_argument("--delay", "-d", type=int, default=30,
                       help="Seconds between personas (rate limit protection)")
    
    args = parser.parse_args()
    
    if args.all:
        persona_names = None  # Will use all 7
    else:
        persona_names = [n.strip() for n in args.personas.split(",")]
    
    await run_pipeline(
        target_url=args.url,
        task=args.task,
        persona_names=persona_names,
        delay_between=args.delay,
    )


if __name__ == "__main__":
    asyncio.run(main())
