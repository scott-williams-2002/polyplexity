"""
Prompts for research synthesis and query generation.
Used by the researcher subgraph nodes.
"""

RESEARCH_SYNTHESIS_PROMPT_TEMPLATE = """For context, the current date is {current_date}.

Analyze the following search results about '{topic}'. Write a detailed summary of the findings. Ignore irrelevant info.

IMPORTANT: Maintain inline links with facts using markdown format: [link text](url).
When citing information from sources, preserve the source URLs inline with the facts.
Format links as markdown: [descriptive text](source_url).

{raw_data}"""

