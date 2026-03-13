"""
Parallax — Cognitive Model Logic
Behavioral rules that influence how persona agents interact with web pages.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CognitiveModel:
    """
    Models a persona's cognitive state during a browsing session.
    Tracks frustration, confusion, and task progress.
    """
    persona_name: str
    frustration_threshold: int
    current_frustration: int = 0
    steps_taken: int = 0
    max_steps: int = 15
    confusions: list = field(default_factory=list)
    successes: list = field(default_factory=list)
    has_given_up: bool = False
    
    def record_frustration(self, reason: str) -> bool:
        """
        Record a frustration event. Returns True if persona has given up.
        """
        self.current_frustration += 1
        self.confusions.append({
            "step": self.steps_taken,
            "reason": reason,
            "frustration_level": self.current_frustration,
        })
        
        if self.current_frustration >= self.frustration_threshold:
            self.has_given_up = True
            return True
        return False
    
    def record_success(self, action: str):
        """Record a successful action."""
        self.successes.append({
            "step": self.steps_taken,
            "action": action,
        })
        # Success slightly reduces frustration
        self.current_frustration = max(0, self.current_frustration - 1)
    
    def step(self):
        """Increment step counter."""
        self.steps_taken += 1
    
    def should_continue(self) -> bool:
        """Check if the persona should keep browsing."""
        if self.has_given_up:
            return False
        if self.steps_taken >= self.max_steps:
            return False
        return True
    
    def get_state_summary(self) -> dict:
        """Get a summary of the cognitive state for logging."""
        return {
            "persona": self.persona_name,
            "steps_taken": self.steps_taken,
            "frustration": f"{self.current_frustration}/{self.frustration_threshold}",
            "has_given_up": self.has_given_up,
            "confusions": len(self.confusions),
            "successes": len(self.successes),
        }
