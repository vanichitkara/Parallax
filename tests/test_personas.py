"""
Tests for persona definitions and cognitive models.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personas.definitions import PERSONAS, get_persona_by_name, Persona
from personas.cognitive import CognitiveModel


def test_all_personas_exist():
    """Verify all 7 personas are defined."""
    assert len(PERSONAS) == 7, f"Expected 7 personas, got {len(PERSONAS)}"
    names = [p.name for p in PERSONAS]
    assert "Martha" in names
    assert "Raj" in names
    assert "Yuki" in names
    assert "Sam" in names
    assert "Dev" in names
    assert "Priya" in names
    assert "Carlos" in names
    print("✅ All 7 personas exist")


def test_persona_lookup():
    """Verify persona lookup by name works."""
    martha = get_persona_by_name("martha")
    assert martha.name == "Martha"
    assert martha.age == 72
    assert martha.tech_level == 2
    
    raj = get_persona_by_name("RAJ")  # case insensitive
    assert raj.name == "Raj"
    assert raj.tech_level == 10
    
    print("✅ Persona lookup works")


def test_persona_prompts_are_distinct():
    """Verify each persona generates a DIFFERENT prompt."""
    prompts = [p.to_prompt_context() for p in PERSONAS]
    
    # All prompts should be unique
    assert len(set(prompts)) == len(prompts), "Duplicate prompts found!"
    
    # Check key persona-specific content
    martha_prompt = get_persona_by_name("martha").to_prompt_context()
    assert "72-year-old" in martha_prompt
    assert "do NOT recognize icon-only buttons" in martha_prompt
    
    sam_prompt = get_persona_by_name("sam").to_prompt_context()
    assert "screen reader" in sam_prompt.lower()
    assert "heading structure" in sam_prompt.lower()
    
    yuki_prompt = get_persona_by_name("yuki").to_prompt_context()
    assert "English is NOT your first language" in yuki_prompt
    
    carlos_prompt = get_persona_by_name("carlos").to_prompt_context()
    assert "deuteranopia" in carlos_prompt
    assert "red/green" in carlos_prompt
    
    print("✅ All persona prompts are distinct and contain persona-specific content")


def test_cognitive_model():
    """Test the cognitive model frustration tracking."""
    model = CognitiveModel(
        persona_name="TestUser",
        frustration_threshold=3,
    )
    
    # Initial state
    assert model.current_frustration == 0
    assert model.should_continue() == True
    assert model.has_given_up == False
    
    # Record frustrations
    gave_up = model.record_frustration("confusing button")
    assert gave_up == False
    assert model.current_frustration == 1
    
    gave_up = model.record_frustration("broken link")
    assert gave_up == False
    assert model.current_frustration == 2
    
    gave_up = model.record_frustration("can't find nav")
    assert gave_up == True  # Threshold reached!
    assert model.current_frustration == 3
    assert model.has_given_up == True
    assert model.should_continue() == False
    
    print("✅ Cognitive model frustration tracking works correctly")


def test_cognitive_model_success_reduces_frustration():
    """Test that success reduces frustration."""
    model = CognitiveModel(
        persona_name="TestUser",
        frustration_threshold=5,
    )
    
    model.record_frustration("issue 1")
    model.record_frustration("issue 2")
    assert model.current_frustration == 2
    
    model.record_success("found the button")
    assert model.current_frustration == 1  # Reduced by 1
    
    model.record_success("completed step")
    assert model.current_frustration == 0  # Minimum is 0
    
    model.record_success("another success")
    assert model.current_frustration == 0  # Stays at 0
    
    print("✅ Success reduces frustration correctly")


def test_cognitive_model_max_steps():
    """Test max step limit."""
    model = CognitiveModel(
        persona_name="TestUser",
        frustration_threshold=100,  # Won't give up from frustration
        max_steps=3,
    )
    
    assert model.should_continue() == True
    model.step()
    model.step()
    model.step()
    assert model.should_continue() == False  # Max steps reached
    
    print("✅ Max step limit works correctly")


def test_persona_tech_levels_vary():
    """Verify personas have diverse tech levels."""
    tech_levels = [p.tech_level for p in PERSONAS]
    assert min(tech_levels) <= 3, "Should have low-tech personas"
    assert max(tech_levels) >= 8, "Should have high-tech personas"
    
    # Verify specific relationships
    martha = get_persona_by_name("martha")
    raj = get_persona_by_name("raj")
    assert raj.tech_level > martha.tech_level, "Raj should be more tech-savvy than Martha"
    
    print("✅ Tech levels are diverse")


def test_frustration_thresholds_vary():
    """Verify personas have different frustration thresholds."""
    thresholds = [p.cognitive_traits.frustration_threshold for p in PERSONAS]
    assert min(thresholds) <= 3, "Should have impatient personas"
    assert max(thresholds) >= 6, "Should have patient personas"
    
    dev = get_persona_by_name("dev")
    raj = get_persona_by_name("raj")
    assert dev.cognitive_traits.frustration_threshold < raj.cognitive_traits.frustration_threshold, \
        "Dev (teen) should be more impatient than Raj (engineer)"
    
    print("✅ Frustration thresholds are diverse")


if __name__ == "__main__":
    test_all_personas_exist()
    test_persona_lookup()
    test_persona_prompts_are_distinct()
    test_cognitive_model()
    test_cognitive_model_success_reduces_frustration()
    test_cognitive_model_max_steps()
    test_persona_tech_levels_vary()
    test_frustration_thresholds_vary()
    
    print(f"\n{'='*40}")
    print("✅ ALL PERSONA TESTS PASSED!")
    print(f"{'='*40}")
