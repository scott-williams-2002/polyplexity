#!/usr/bin/env python3
"""
Run market research subgraph with real LLM calls.

This script hardcodes a user request and AI-generated report, then runs
the market research subgraph to find relevant prediction markets.
"""
import json
import re
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from polyplexity_agent.config import Settings
from polyplexity_agent.graphs.state import MarketResearchState
from polyplexity_agent.graphs.subgraphs.market_research import (
    market_research_graph,
    set_state_logger,
)
from polyplexity_agent.streaming import process_custom_events
from polyplexity_agent.utils.helpers import log_node_state
from polyplexity_agent.utils.state_logger import StateLogger


# Hardcoded user request and AI-generated report
USER_REQUEST = "how do I use cursor rules"

AI_GENERATED_REPORT = """
Cursor rules let you customize how the AI writes code globally and per-project. They’re just instructions the agent reads before responding so it can follow your style, stack, and conventions.  

## What cursor rules are

Cursor rules are system-style instructions that the editor automatically prepends to your prompts so the AI behaves consistently with your preferences. They can enforce things like “always use TypeScript,” project architecture patterns, or how to handle errors and tests.[3][5][6]

## Where rules live

There are two main scopes:  
- Global/user rules: set in Cursor’s settings and apply across all projects for your personal preferences (languages, style, etc.).[1][3]
- Project rules: stored as `.mdc` (or similar) files under `.cursor/rules` in your repo, and only affect that project.[2][3]

## Creating rules via UI

In the Cursor app, open Settings and go to the Rules section, where you can add user rules and project rules from the sidebar. For project rules, Cursor will create a rule file under `.cursor/rules` that you then edit with descriptions, file globs, and instructions.[5][1][2][3]

## Creating rules via files/CLI

You can also create rule files directly in `.cursor/rules`, writing markdown-like content that describes when they apply and what the AI should do. Some workflows use a small CLI (`cursor-rules`) to scaffold a set of rule files for a project in one shot.[6][2][3]

## Attaching rules to contexts

Each rule can specify how and when it’s applied: always, auto-attached based on file patterns, only when the agent requests it, or manual. You typically configure this at the top of the rule file and optionally use globs like `*.ts` or folders so the rule only kicks in for relevant files.[7][3][6]

## What to put in rules

Rules work best when they encode concrete patterns: preferred frameworks and libraries, file/folder structure, code style, and “do/don’t” examples for patterns you want to avoid. Including small, focused code examples and explicit notes about deprecated patterns helps the AI generate more robust, idiomatic code for your project.[3][6]

[1](https://www.youtube.com/watch?v=IsXrCBlAshg)
[2](https://www.devshorts.in/p/how-to-use-cursor-rules)
[3](https://cursor101.com/cursor/rules)
[4](https://www.youtube.com/watch?v=Vy7dJKv1EpA)
[5](https://workos.com/blog/what-are-cursor-rules)
[6](https://trigger.dev/blog/cursor-rules)
[7](https://www.lullabot.com/articles/supercharge-your-ai-coding-cursor-rules-and-memory-banks)
[8](https://www.youtube.com/watch?v=sxqq9Eql6Cc)
[9](https://www.reddit.com/r/cursor/comments/1ik06ol/a_guide_to_understand_new_cursorrules_in_045/)
[10](https://forum.cursor.com/t/best-practices-cursorrules/41775)
"""


def print_stream_event(mode: str, data: Any) -> None:
    """
    Print streaming event to console in readable format.
    
    Args:
        mode: Stream mode ("custom", "updates", or "values")
        data: Event data dictionary
    """
    if mode == "custom":
        events = process_custom_events(mode, data)
        for event in events:
            event_type = event.get("type", "unknown")
            node = event.get("node", "unknown")
            event_name = event.get("event", "unknown")
            payload = event.get("payload", {})
            
            print(f"\n[{event_type.upper()}] {node} - {event_name}")
            if payload:
                print(f"  Payload: {json.dumps(payload, indent=2, default=str)}")
    
    elif mode == "updates":
        if isinstance(data, dict):
            for node_name, node_data in data.items():
                print(f"\n[STATE_UPDATE] {node_name}")
                if isinstance(node_data, dict):
                    for key, value in node_data.items():
                        if isinstance(value, (list, dict)):
                            print(f"  {key}: {json.dumps(value, indent=2, default=str)[:200]}...")
                        else:
                            print(f"  {key}: {value}")
    
    elif mode == "values":
        if isinstance(data, dict):
            print(f"\n[FINAL_STATE]")
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    print(f"  {key}: {json.dumps(value, indent=2, default=str)[:200]}...")
                else:
                    print(f"  {key}: {value}")


def run_market_research_with_streaming(
    user_request: str,
    ai_report: str,
    graph: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Run market research subgraph with console streaming output.
    
    Args:
        user_request: The original user request/question
        ai_report: The AI-generated report that needs market data
        graph: Optional graph instance (creates default if None)
        
    Returns:
        Final state dictionary with approved_markets
    """
    if graph is None:
        graph = market_research_graph
    
    # Use user request as the topic for market research
    topic = user_request
    
    settings = Settings()
    settings.state_logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_topic = re.sub(r'[^\w\s-]', '', topic)[:50].strip().replace(' ', '_')
    log_filename = f"market_research_{timestamp}_{sanitized_topic}.txt"
    log_path = settings.state_logs_dir / log_filename
    
    state_logger = StateLogger(log_path)
    set_state_logger(state_logger)
    
    initial_state: MarketResearchState = {
        "original_topic": topic,
        "market_queries": [],
        "raw_events": [],
        "candidate_markets": [],
        "approved_markets": [],
        "reasoning_trace": [],
    }
    
    log_node_state(
        state_logger,
        "START",
        "SUBGRAPH",
        dict(initial_state),
        "INITIAL",
        additional_info=f"User Request: {user_request}\nAI Report: {ai_report[:200]}..."
    )
    
    print(f"\n{'='*80}")
    print(f"Starting Market Research Subgraph")
    print(f"{'='*80}")
    print(f"\nUSER REQUEST:")
    print(f"{user_request}")
    print(f"\nAI GENERATED REPORT:")
    print(f"{ai_report[:500]}...")
    print(f"\n{'='*80}\n")
    
    final_state = initial_state.copy()
    
    try:
        for mode, data in graph.stream(
            initial_state,
            stream_mode=["custom", "updates", "values"]
        ):
            print_stream_event(mode, data)
            
            if mode == "updates":
                if isinstance(data, dict):
                    for node_name, node_data in data.items():
                        if isinstance(node_data, dict):
                            final_state.update(node_data)
                            log_node_state(
                                state_logger,
                                f"{node_name}_UPDATE",
                                "SUBGRAPH",
                                dict(node_data),
                                "STREAM_UPDATE",
                                additional_info=f"State update from {node_name}"
                            )
            elif mode == "values":
                if isinstance(data, dict):
                    final_state.update(data)
        
    finally:
        if state_logger:
            state_logger.close()
            print(f"\n{'='*80}")
            print(f"State log saved to: {log_path.absolute()}")
            print(f"{'='*80}\n")
        set_state_logger(None)
    
    return final_state if final_state else {}


def main():
    """Run market research subgraph with hardcoded user request and AI report."""
    print(f"\n{'='*80}")
    print(f"Running Market Research Subgraph")
    print(f"{'='*80}")
    print(f"\nUsing hardcoded inputs:")
    print(f"User Request: {USER_REQUEST}")
    print(f"AI Report Length: {len(AI_GENERATED_REPORT)} characters")
    print(f"{'='*80}\n")
    
    try:
        result = run_market_research_with_streaming(USER_REQUEST, AI_GENERATED_REPORT)
        
        print(f"\n{'='*80}")
        print("RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"User Request: {USER_REQUEST}")
        print(f"Market Queries Generated: {len(result.get('market_queries', []))}")
        print(f"Raw Markets Found: {len(result.get('raw_events', []))}")
        print(f"Candidate Markets Ranked: {len(result.get('candidate_markets', []))}")
        print(f"Approved Markets: {len(result.get('approved_markets', []))}")
        
        if result.get('approved_markets'):
            print(f"\n{'='*80}")
            print("APPROVED MARKETS:")
            print(f"{'='*80}")
            for i, market in enumerate(result['approved_markets'], 1):
                print(f"\n{i}. {market.get('question', 'N/A')}")
                print(f"   Slug: {market.get('slug', 'N/A')}")
                print(f"   ClobTokenIds: {market.get('clobTokenIds', [])}")
                print(f"   Image: {market.get('image', 'N/A')}")
                if market.get('description'):
                    desc = market['description'][:200] + "..." if len(market.get('description', '')) > 200 else market.get('description', '')
                    print(f"   Description: {desc}")
        
        if result.get('reasoning_trace'):
            print(f"\n{'='*80}")
            print("REASONING TRACE:")
            print(f"{'='*80}")
            for reasoning in result['reasoning_trace']:
                print(f"- {reasoning}")
        
        print(f"\n{'='*80}")
        print("Full result saved to state log file (see path above)")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print("ERROR:")
        print(f"{'='*80}")
        print(f"{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
