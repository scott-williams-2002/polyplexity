"""
Prompts for the Market Research subgraph.

Used for generating Polymarket search queries, ranking markets, and evaluating market quality.
"""

MARKET_QUERY_GENERATION_PROMPT = """You are a Market Research Query Planner. Your task is to transform a user's research topic into effective search queries for Polymarket (a prediction market platform).

Your goal: Generate 2-4 distinct search queries that will help find relevant prediction markets on Polymarket related to the user's topic.

Rules:
1. Each query should target different aspects or angles of the topic
2. Focus on terms that would appear in prediction market questions
3. Consider political, economic, sports, entertainment, or other market categories
4. Use keywords that are likely to match Polymarket event titles and descriptions
5. Avoid overly generic terms - be specific to the topic

Topic: {original_topic}

Generate search queries as a JSON object with a "queries" field containing a list of strings.
Example format: {{"queries": ["query 1", "query 2", "query 3"]}}

Return only valid JSON."""

MARKET_RANKING_PROMPT = """You are a Market Research Analyst. Your task is to rank and filter prediction markets from Polymarket based on their relevance to the user's research topic.

Your goal: Analyze the candidate markets and rank them by relevance, filtering out irrelevant ones.

Rules:
1. Rank markets by how directly they relate to the original topic
2. Consider market question clarity and specificity
3. Prioritize markets with clear, answerable questions
4. Filter out markets that are only tangentially related
5. Return the top-ranked markets in order of relevance

Original Topic: {original_topic}

Candidate Markets:
{candidate_markets}

Return a JSON object with a "ranked_markets" field containing a list of the ranked market dictionaries.
Example format: {{"ranked_markets": [{{"question": "...", "slug": "...", ...}}, ...]}}

Return only valid JSON."""

MARKET_EVALUATION_PROMPT = """You are a Market Quality Evaluator. Your task is to evaluate ranked prediction markets and determine if they meet quality standards for inclusion in research.

Your goal: Review the ranked markets and decide whether they are high-quality and relevant enough to approve for the final report.

Evaluation Criteria:
1. Relevance: Does the market directly relate to the original topic?
2. Clarity: Is the market question clear and well-defined?
3. Quality: Is the market information complete and useful?
4. Value: Would this market add value to the research report?

Original Topic: {original_topic}

Ranked Markets:
{ranked_markets}

Return a JSON object with:
- "decision": "APPROVE" or "REJECT"
- "markets": List of approved market dictionaries (empty if REJECT)

Example format: {{"decision": "APPROVE", "markets": [{{"question": "...", "slug": "...", ...}}, ...]}}

Return only valid JSON."""
