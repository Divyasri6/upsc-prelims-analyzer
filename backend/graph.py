# graph.py
from langgraph.graph import StateGraph, END
import os

from models import AgentState
from node import (
    plan_node,
    llm_subject_tagging_node,
    evaluate_node,
    mindset_inference_node,
    subject_analysis_node,
    unattempted_analysis_node,
    summary_report_node
)

# --- Conditional Edges ---
def should_continue_evaluating(state: AgentState) -> str:
    if state["current_question_index"] < len(state["all_questions"]):
        return "continue_evaluation"
    else:
        return "evaluation_complete"

# --- Building the LangGraph ---
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("planner", plan_node)
workflow.add_node("llm_subject_tagging", llm_subject_tagging_node)
workflow.add_node("evaluate_question", evaluate_node)
workflow.add_node("mindset_inference", mindset_inference_node)
workflow.add_node("subject_analysis", subject_analysis_node)
workflow.add_node("unattempted_analysis", unattempted_analysis_node)
workflow.add_node("summary_report", summary_report_node)

# Set entry point
workflow.set_entry_point("planner")

# Add edges
workflow.add_edge("planner", "llm_subject_tagging")
workflow.add_edge("llm_subject_tagging", "evaluate_question")

# Conditional edge for evaluation loop
workflow.add_conditional_edges(
    "evaluate_question",
    should_continue_evaluating,
    {
        "continue_evaluation": "evaluate_question",
        "evaluation_complete": "mindset_inference"
    }
)

workflow.add_edge("mindset_inference", "subject_analysis")
workflow.add_edge("subject_analysis", "unattempted_analysis")
workflow.add_edge("unattempted_analysis", "summary_report")
workflow.add_edge("summary_report", END)

# Compile the graph
langgraph_app = workflow.compile()
print("\n--- LangGraph Workflow Compiled Successfully ---")

