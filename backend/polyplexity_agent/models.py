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
    answer_format: Literal["concise", "report"] = Field(
        description="Select 'concise' for standard Q&A (bullet points, natural language). Select 'report' ONLY if the user explicitly asks for a report, comprehensive study, or in-depth analysis.",
        default="concise"
    )
    reasoning: str = Field(description="Brief reasoning for the decision.")


class MarketQueries(BaseModel):
    """
    Output model for generating market search queries.
    
    Used by the market query generation node to structure the LLM's response
    into a list of distinct search queries for Polymarket.
    """
    queries: List[str] = Field(description="List of distinct search queries for Polymarket.")


class RankedMarkets(BaseModel):
    """
    Output model for ranking markets by relevance.
    
    Used by the process and rank markets node to structure the LLM's response
    with ranked market slugs and reasoning.
    """
    slugs: List[str] = Field(description="List of market slugs ranked by relevance to the topic.")
    reasoning: str = Field(description="Brief explanation of why these markets were selected and ranked.")


class ApprovedMarkets(BaseModel):
    """
    Output model for evaluating and approving markets.
    
    Used by the evaluate markets node to structure the LLM's response
    with approved market slugs and reasoning.
    """
    slugs: List[str] = Field(description="List of approved market slugs that meet quality standards.")
    reasoning: str = Field(description="Brief explanation of why these markets were approved or rejected.")


class SelectedTags(BaseModel):
    """
    Output model for selecting tags from a batch.
    
    Used by the tag selection node to structure the LLM's response
    with selected tag names and reasoning.
    """
    selected_tag_names: List[str] = Field(
        description="List of tag names selected from the current batch. Must match exactly as shown (preserve case and spacing)."
    )
    reasoning: str = Field(description="Brief explanation of why these tags were selected.")
    continue_search: bool = Field(
        description="Whether to fetch more batches (true if fewer than 10 tags selected and more tags may be available)."
    )

