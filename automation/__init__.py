"""Universal desktop automation planning and execution primitives."""

from automation.plan import AutomationPlan, AutomationStep
from automation.planner import build_automation_plan
from automation.executor import execute_automation_plan

__all__ = ["AutomationPlan", "AutomationStep", "build_automation_plan", "execute_automation_plan"]
