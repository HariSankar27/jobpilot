from langgraph.graph import END, START, StateGraph

from .nodes import (
    apply_review,
    human_review,
    parse_job,
    render_pdf,
    route_after_review,
    route_after_verify,
    select_facts,
    verify_claims,
    write_bullets,
)
from .state import TailorState


def build_graph(checkpointer):
    g = StateGraph(TailorState)
    g.add_node("parse_job", parse_job)
    g.add_node("select_facts", select_facts)
    g.add_node("write_bullets", write_bullets)
    g.add_node("verify_claims", verify_claims)
    g.add_node("human_review", human_review)
    g.add_node("apply_review", apply_review)
    g.add_node("render_pdf", render_pdf)
    g.add_edge(START, "parse_job")
    g.add_edge("parse_job", "select_facts")
    g.add_edge("select_facts", "write_bullets")
    g.add_edge("write_bullets", "verify_claims")
    g.add_conditional_edges("verify_claims", route_after_verify, ["write_bullets", "human_review"])
    g.add_edge("human_review", "apply_review")
    g.add_conditional_edges("apply_review", route_after_review, ["human_review", "render_pdf"])
    g.add_edge("render_pdf", END)
    return g.compile(checkpointer=checkpointer)
