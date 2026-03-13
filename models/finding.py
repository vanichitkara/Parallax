"""
Parallax — UX Finding Data Model
Represents a UX issue discovered by persona agents.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"      # Blocks task completion entirely
    HIGH = "high"              # Causes significant confusion/frustration
    MEDIUM = "medium"          # Noticeable issue but workaround exists
    LOW = "low"                # Minor annoyance
    INFO = "info"              # Observation, not necessarily an issue


class IssueCategory(str, Enum):
    NAVIGATION = "navigation"
    READABILITY = "readability"
    ACCESSIBILITY = "accessibility"
    VISUAL_DESIGN = "visual_design"
    INTERACTION = "interaction"
    LANGUAGE = "language"
    COLOR = "color"
    MOBILE = "mobile"
    PERFORMANCE = "performance"
    COGNITIVE_LOAD = "cognitive_load"


class UXFinding(BaseModel):
    """A UX issue discovered during persona testing."""
    finding_id: str
    
    # What was found
    title: str = Field(description="Short description of the issue")
    description: str = Field(description="Detailed description")
    
    # Categorization
    severity: Severity
    category: IssueCategory
    
    # Who found it
    affected_personas: list[str] = Field(description="Names of personas affected")
    affected_count: int = Field(description="Number of personas affected (out of total)")
    total_personas: int = Field(default=7, description="Total number of personas tested")
    
    # Evidence
    page_url: str
    screenshot_urls: list[str] = Field(default_factory=list)
    
    # Fix recommendation
    recommendation: str = Field(description="Recommended fix")
    wcag_guideline: Optional[str] = Field(default=None, description="Related WCAG guideline if applicable")
    
    # Impact score (calculated)
    impact_score: float = Field(default=0.0, description="Calculated impact score 0-100")
    
    def calculate_impact(self):
        """Calculate impact score based on severity and affected personas."""
        severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.75,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.25,
            Severity.INFO: 0.1,
        }
        persona_ratio = self.affected_count / self.total_personas
        self.impact_score = round(
            severity_weights[self.severity] * persona_ratio * 100, 1
        )
