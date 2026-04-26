"""
Parallax — Journey Data Models
Represents a persona's step-by-step journey through a website.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    KEY_PRESS = "key_press"
    SCREENSHOT = "screenshot"
    GIVE_UP = "give_up"
    TASK_COMPLETE = "task_complete"


class JourneyStep(BaseModel):
    """A single step in a persona's journey through a website."""
    step_number: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # What the agent saw
    observation: str = Field(description="What the persona observed on the screen")
    
    # What the agent thought (persona-specific reasoning)
    thinking: str = Field(description="The persona's internal thought process")
    
    # What action was taken
    action_type: ActionType
    action_details: dict = Field(default_factory=dict, description="Action parameters (coordinates, text, etc.)")
    
    # Outcome
    outcome: str = Field(description="What happened after the action")
    
    # Emotional state
    frustration_level: int = Field(ge=0, le=10, description="Current frustration 0-10")
    confusion_points: list[str] = Field(default_factory=list, description="Specific things that confused the persona")
    ux_issues: list[dict] = Field(default_factory=list, description="UX issues identified in this step")
    
    # Screenshot reference
    screenshot_base64: Optional[str] = Field(default=None, description="Base64 encoded screenshot")
    screenshot_url: Optional[str] = Field(default=None, description="Cloud Storage URL for screenshot")
    
    # Page context
    page_url: Optional[str] = None
    page_title: Optional[str] = None


class Journey(BaseModel):
    """A complete journey of a persona through a website."""
    journey_id: str
    persona_name: str
    persona_age: int
    persona_tech_level: int = 0
    persona_background: str
    target_url: str
    task: str
    
    # Journey metadata
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    
    # Steps
    steps: list[JourneyStep] = Field(default_factory=list)
    
    # Outcome
    task_completed: bool = False
    gave_up: bool = False
    gave_up_reason: Optional[str] = None
    total_steps: int = 0
    max_frustration_reached: int = 0
    
    # Summary
    key_confusions: list[str] = Field(default_factory=list)
    key_successes: list[str] = Field(default_factory=list)
    overall_difficulty: Optional[str] = None  # easy, moderate, hard, impossible
    
    def add_step(self, step: JourneyStep):
        """Add a step to the journey."""
        self.steps.append(step)
        self.total_steps = len(self.steps)
        if step.frustration_level > self.max_frustration_reached:
            self.max_frustration_reached = step.frustration_level
        self.key_confusions.extend(step.confusion_points)
    
    def complete(self, success: bool, reason: Optional[str] = None):
        """Mark the journey as complete."""
        self.completed_at = datetime.utcnow().isoformat()
        self.task_completed = success
        if not success:
            self.gave_up = True
            self.gave_up_reason = reason
