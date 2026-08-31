from __future__ import annotations

from crewai import Crew

from .crew import build_content_crew, build_research_crew
from .models import ProjectBrief


def run_research_pipeline(brief: ProjectBrief):
    crew: Crew = build_research_crew(brief=brief)
    return crew.kickoff()


def run_content_pipeline(brief: ProjectBrief):
    crew: Crew = build_content_crew(brief=brief)
    return crew.kickoff()

