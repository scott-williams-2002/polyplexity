"""
Pydantic models for structured outputs used by the research agent.
These models define the schema for LLM responses that require structured formatting.
"""
from typing import List, Literal

from pydantic import BaseModel, Field


class SearchQueries(BaseModel):
    """
    Output model for generating search queries.
    
    Used by the query generation node to structure the LLM's response
    into a list of distinct search queries.
    """
    queries: List[str] = Field(description="List of distinct search queries.")


class SupervisorDecision(BaseModel):
    """
    Output model for the supervisor's decision-making process.
    
    Used by the supervisor node to structure the LLM's decision about
    whether to continue researching or finish and generate the final report.
    """
    next_step: Literal["research", "finish", "clarify"] = Field(
        description="Choose 'research' if more information is needed, 'finish' if you have sufficient information, or 'clarify' if input is ambiguous."
    )
    research_topic: str = Field(
        description="If researching, the specific topic to investigate next. If finishing, clarifying, or answering directly, leave empty.",
        default=""
    )
    research_iterations: int = Field(
        description="Number of research iterations needed. -1 for clarification, 0 for direct answer, 1-3 for research loops.",
        ge=-1,
        le=3
    )
    query_breadth: int = Field(
        description="Depth of research (Tavily results per query). Standard is 3-5.",
        ge=3,
        le=5,
        default=4
    )
    reasoning: str = Field(description="Brief reasoning for the decision.")

