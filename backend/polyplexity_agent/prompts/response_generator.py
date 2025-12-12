"""
Prompts for generating the final response (report or concise answer).
"""

# Base instructions for different formats

# Instructions for concise, direct answers (default format).
# Emphasizes readability, summary headers, and inline markdown citations.
FORMAT_INSTRUCTIONS_CONCISE = """
FORMATTING REQUIREMENTS (CONCISE):
- Answer directly with a clear summary sentence or paragraph (1-3 sentences) to start.
- Use simple headers (###) to organize key points if helpful.
- Use bullet points for lists.
- Use concise paragraphs for explanations.
- CRITICAL: You MUST cite all sources used inline.
- Citation format: [fact or source name](url).
- Ensure all links are valid markdown.
- Do not use tables.
- Focus on the answer, not the research process.
"""

# Instructions for comprehensive reports (requested by user).
# Allows for more structure, tables, and in-depth analysis, with strict citation rules.
FORMAT_INSTRUCTIONS_REPORT = """
FORMATTING REQUIREMENTS (REPORT):
- No more than 300 words.
- Write a comprehensive, well-structured report.
- Use proper markdown headers (#, ##, ###).
- Use lists for readability.
- CRITICAL: You MUST cite all sources used inline.
- Citation format: [fact or source name](url).
- You may use tables for comparisons or data if appropriate (max 1 table).
- Preserve all source links and ensure they are valid markdown.
- Structure with clear introduction, body sections, and conclusion.
"""

# Main prompt for generating the initial response from research notes.
# Injects the appropriate formatting instructions based on user preference.
FINAL_RESPONSE_PROMPT_TEMPLATE = """For context, the current date is {current_date}.

Based on the following research notes, write a response to: {user_request}

{formatting_instructions}

Notes:
{notes}"""

# Prompt for refining an existing response based on follow-up questions.
# Handles integrating new research notes into an existing report/answer.
FINAL_RESPONSE_REFINEMENT_PROMPT_TEMPLATE = """For context, the current date is {current_date}.

This is a REFINEMENT of an existing response (Version {version}).
The user has asked a follow-up question: {user_request}

Previous Response (Version {version}):
{existing_report}

New Research Notes:
{notes}

TASK: Refine and expand the response based on:
- The new research notes provided above
- The user's follow-up question
- Integrate new findings with existing content

{formatting_instructions}

Clearly indicate what's new vs. what was already covered."""

# Prompt for direct answers that don't require research (0 iterations).
# Used when the supervisor determines the query can be answered immediately.
DIRECT_ANSWER_PROMPT_TEMPLATE = """You are a helpful assistant. Answer the user's request directly.

Conversation Summary:
{conversation_summary}

User Request: {user_request}

FORMATTING:
- Provide a clear summary header or title.
- Write 1-3 sentences of explanation or context.
- Use bullet points if listing items.
- Use simple markdown headers (###) to separate sections if needed.
- Be concise but complete.
- If referencing general knowledge, no citations are needed, but if citing specific facts from context, use [source](url).
"""

# Prompt for generating a convincing salesman-like blurb connecting user's question to Polymarket markets.
# Used to create a natural, compelling recommendation that ties the user's original question to relevant markets.
POLYMARKET_BLURB_PROMPT_TEMPLATE = """You are a helpful assistant creating a natural, convincing recommendation connecting a user's question to relevant Polymarket prediction markets.

User's Original Question: {user_request}

AI Response Summary: {final_report_summary}

Approved Markets:
{markets_info}

TASK: Write a brief, convincing blurb (2-4 sentences) that:
1. References the user's original question naturally
2. Connects it to one or more of the approved markets
3. Makes it sound like a natural, helpful recommendation
4. Explains why these markets might be interesting based on what was discussed

FORMATTING REQUIREMENTS:
- Structure the text in markdown format
- Use **bold** text to emphasize key points
- You may include a few bullet points if helpful
- Do NOT use tables
- Keep the entire section brief and concise

EXAMPLES:
- "Based on your question about hot rods, you might be interested in testing your knowledge on this Polymarket market about NASCAR because..."
- "We just talked about the history of sports in my response, you should check out what people think the Mavericks game result will be..."

Be conversational, natural, and compelling. Focus on making the connection clear and interesting.
"""
