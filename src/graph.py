"""Writer-Critic loop built with LangGraph."""
import os
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

MAX_REVISIONS = 3
PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()  # "gemini" (free) or "anthropic"
DEFAULT_MODELS = {"gemini": "gemini-3.5-flash-lite", "anthropic": "claude-sonnet-4-6"}
MODEL = os.getenv("MODEL_NAME", DEFAULT_MODELS.get(PROVIDER, ""))


class State(TypedDict):
    topic: str
    draft: str
    feedback: str
    approved: bool
    revisions: int


def _llm():
    if PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=MODEL, temperature=0.7, max_tokens=800)
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=MODEL)


def _ask(prompt: str) -> str:
    """Call the LLM and always return plain text."""
    content = _llm().invoke(prompt).content
    if isinstance(content, list):
        content = "".join(
            part if isinstance(part, str) else part.get("text", "") for part in content
        )
    return content.strip()


def writer(state: State) -> dict:
    """Draft (or revise) a short paragraph on the topic."""
    prompt = f"Write a short, engaging paragraph (max 80 words) about: {state['topic']}."
    if state.get("feedback"):
        prompt += (
            f"\n\nPrevious draft:\n{state['draft']}\n\n"
            f"Critic feedback:\n{state['feedback']}\n\nRevise the draft accordingly."
        )
    draft = _ask(prompt)
    return {"draft": draft, "revisions": state.get("revisions", 0) + 1}


def critic(state: State) -> dict:
    """Review the draft. Reply 'APPROVED' or give specific feedback."""
    prompt = (
        "You are a very strict editor. Only approve if the paragraph has a concrete fact or number and no cliches. Review it for clarity, "
        "accuracy and style.\nIf it is good enough, reply with exactly 'APPROVED'.\n"
        "Otherwise give 2-3 concrete suggestions.\n\n"
        f"Paragraph:\n{state['draft']}"
    )
    verdict = _ask(prompt)
    return {"approved": verdict.upper().startswith("APPROVED"), "feedback": verdict}


def route(state: State) -> str:
    """Conditional edge: loop back to the writer or finish."""
    if state["approved"] or state["revisions"] >= MAX_REVISIONS:
        return "end"
    return "revise"


def build_graph():
    g = StateGraph(State)
    g.add_node("writer", writer)
    g.add_node("critic", critic)
    g.add_edge(START, "writer")
    g.add_edge("writer", "critic")
    g.add_conditional_edges("critic", route, {"revise": "writer", "end": END})
    return g.compile()
