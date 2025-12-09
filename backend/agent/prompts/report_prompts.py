"""
Prompts for final report generation.
Used by the orchestrator's final_report_node.
"""

FINAL_REPORT_PROMPT_TEMPLATE = """For context, the current date is {current_date}.

Based on the following research notes, write a comprehensive answer to: {user_request}

FORMATTING REQUIREMENTS:
- Write the answer in markdown format with proper headers, lists, and formatting
- Include inline links with facts using markdown format: [fact or description](source_url)
- Ensure all cited information includes source URLs inline with the facts
- Use proper markdown syntax: headers (# ## ###), lists (- or *), bold (**text**), etc.
- Try to avoid using tables unless listing information or making comparrisons like pros and cons. 
- There should not be more than 1 table per report.
- Preserve all source links from the research notes

Notes:
{notes}"""


FINAL_REPORT_REFINEMENT_PROMPT_TEMPLATE = """For context, the current date is {current_date}.

This is a REFINEMENT of an existing report (Version {version}).
The user has asked a follow-up question: {user_request}

Previous Report (Version {version}):
{existing_report}

New Research Notes:
{notes}

TASK: Refine and expand the existing report based on:
- The new research notes provided above
- The user's follow-up question
- Integrate new findings with existing content
- Preserve valuable information from the previous report
- Update sections that need correction or expansion

FORMATTING REQUIREMENTS:
- Write the refined answer in markdown format with proper headers, lists, and formatting
- Include inline links with facts using markdown format: [fact or description](source_url)
- Ensure all cited information includes source URLs inline with the facts
- Use proper markdown syntax: headers (# ## ###), lists (- or *), bold (**text**), etc.
- Tables can be used when appropriate for comparing data or structured information, but do not excessively use tables - prefer prose, lists, and clear explanations
- Preserve all source links from both old and new research notes
- Clearly indicate what's new vs. what was already covered"""

