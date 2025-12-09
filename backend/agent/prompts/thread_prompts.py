"""
Prompts for thread name generation.
Used by the orchestrator for generating thread titles.
"""

THREAD_NAME_GENERATION_PROMPT_TEMPLATE = """Create a concise thread title (exactly 5 words or less) for this user query: {user_query}

Respond with ONLY the title, no explanation or quotes."""

