# nodes.py
import json
import os # Import os for environment variables
from dotenv import load_dotenv # Import load_dotenv
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic.v1 import BaseModel # Using pydantic.v1

from models import AgentState, QuestionEvaluation, MindsetInsightDetail
from prompt import (
    PLAN_PROMPT,
    EVALUATE_PROMPT,
    MINDSET_PROMPT,
    SUBJECT_ANALYSIS_PROMPT,
    UNATTEMPTED_PROMPT,
    SUMMARY_PROMPT,
    LLM_SUBJECT_PROMPT
)

# --- Environment Variable Setup ---
load_dotenv() # Load environment variables from .env file
model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

# --- Node Definitions ---
def plan_node(state: AgentState):
    print("\n--- Executing Plan Node ---")
    messages = [
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ]
    response = model.invoke(messages)
    print("--- Plan Node Completed ---")
    return {"plan": response.content}

def llm_subject_tagging_node(state: AgentState) -> AgentState:
    print("\n--- Executing LLM Subject Tagging Node ---")
    updated_questions = []
    for question in state["all_questions"]:
        # Only tag if subject is missing or empty
        if "subject" not in question or not question["subject"]:
            prompt = LLM_SUBJECT_PROMPT.format(question_text=question["text"])
            messages = [
                SystemMessage(content="You are a UPSC subject classifier. Respond with only the subject name (e.g., History, Geography, Polity, Economics, Environment, Science, Current Affairs, General)."),
                HumanMessage(content=prompt)
            ]
            try:
                response = model.invoke(messages)
                subject = response.content.strip()
                question["subject"] = subject
                print(f"✅ LLM tagged QID={question['id']} → Subject: {subject}")
            except Exception as e:
                print(f"⚠️ LLM failed to classify QID={question['id']}: {e}")
                question["subject"] = "General" # Fallback to General if LLM fails
        updated_questions.append(question) # Add question (tagged or original) to the new list
    state["all_questions"] = updated_questions # Update the state with potentially tagged questions
    print("--- LLM Subject Tagging Node Completed ---")
    return state

def evaluate_node(state: AgentState) -> AgentState:
    print("\n--- Executing Evaluation Node ---")
    if state["current_question_index"] >= len(state["all_questions"]):
        print("--- Evaluation Node: All questions processed ---")
        return state

    current_q_data = state["all_questions"][state["current_question_index"]]
    state["current_question"] = current_q_data

    # Ensure subject is available for the current question
    # It should have been tagged by llm_subject_tagging_node already
    subject_for_eval = current_q_data.get("subject", "General")

    structured_llm_evaluator = model.with_structured_output(QuestionEvaluation, method="function_calling")

    prompt_text = EVALUATE_PROMPT.format(
        question_id=current_q_data["id"],
        question_text=current_q_data["text"],
        option_a=current_q_data["options"]["A"],
        option_b=current_q_data["options"]["B"],
        option_c=current_q_data["options"]["C"],
        option_d=current_q_data["options"]["D"],
        correct_option=current_q_data["correct_option"],
        chosen_option=current_q_data.get("chosen_option", "UNATTEMPTED"),
        subject=subject_for_eval
    )

    try:
        evaluation_result_obj = structured_llm_evaluator.invoke([HumanMessage(content=prompt_text)])
        evaluation_result_dict = evaluation_result_obj.dict()

        # Ensure 'subject' field from LLM is consistent, or use the one from question data
        if not evaluation_result_dict.get("subject"):
            evaluation_result_dict["subject"] = subject_for_eval

        if "evaluation_results" not in state:
            state["evaluation_results"] = []
        state["evaluation_results"].append(evaluation_result_dict)

    except Exception as e:
        print(f"❌ Error during evaluation_node for QID={current_q_data['id']}: {e}")
        print(f"Prompt used:\n{prompt_text}")
        # Fallback for evaluation result if LLM fails, use the pre-tagged subject
        state["evaluation_results"].append({
            "qid": current_q_data["id"],
            "status": "Unknown",
            "subject": subject_for_eval,
            "error": str(e)
        })

    state["current_question_index"] += 1
    print(f"--- Evaluation Node Processed QID={current_q_data['id']} ---")
    return state


def mindset_inference_node(state: AgentState) -> AgentState:
    print("\n--- Executing mindset_inference_node ---")

    current_mindset_qids = {insight.question_id for insight in state.get("mindset_insights", [])}
    wrong_questions_for_mindset = []

    for q_eval in state.get("evaluation_results", []):
        if q_eval["status"] == "Wrong" and q_eval["qid"] not in current_mindset_qids:
            q_orig = next((q for q in state["all_questions"] if q["id"] == q_eval["qid"]), None)
            required_keys = ["id", "text", "options", "correct_option", "chosen_option"]
            if q_orig and all(k in q_orig for k in required_keys):
                wrong_questions_for_mindset.append(q_orig)
            else:
                print(f"⚠️ Skipping malformed question for mindset analysis: {q_orig}")

    if "mindset_insights" not in state:
        state["mindset_insights"] = []

    structured_llm_mindset = model.with_structured_output(MindsetInsightDetail, method="function_calling")

    for q_data in wrong_questions_for_mindset:
        try:
            subject = next(
                (q_eval["subject"] for q_eval in state["evaluation_results"] if q_eval["qid"] == q_data["id"]),
                "Unknown"
            )

            prompt_text = MINDSET_PROMPT.format(
                question_id=q_data["id"],
                question_text=q_data["text"],
                option_a=q_data["options"]["A"],
                option_b=q_data["options"]["B"],
                option_c=q_data["options"]["C"],
                option_d=q_data["options"]["D"],
                correct_option=q_data["correct_option"],
                chosen_option=q_data["chosen_option"],
                subject=subject
            )

            messages = [
                SystemMessage(content="You are a highly analytical cognitive expert. Provide the analysis in JSON format, strictly adhering to the MindsetInsightDetail schema."),
                HumanMessage(content=prompt_text)
            ]

            mindset_insight_obj = structured_llm_mindset.invoke(messages)
            state["mindset_insights"].append(mindset_insight_obj)
            print(f"✅ Generated mindset insight for QID={q_data['id']}")

        except Exception as e:
            print(f"❌ Error generating mindset insight for QID={q_data['id']}: {e}")
            continue

    print("--- Mindset Inference Node Completed ---")
    return state

def subject_analysis_node(state: AgentState) -> AgentState:
    print("\n--- Executing Subject Analysis Node ---")
    evaluated_data = state.get("evaluation_results", [])
    if not evaluated_data:
        state["subject_performance"] = {"error": "No evaluation data available."}
        print("--- Subject Analysis Node Completed: No data ---")
        return state

    subject_raw_data = {}
    for eval_item in evaluated_data:
        subject = eval_item.get("subject", "General")
        status = eval_item["status"]
        if subject not in subject_raw_data:
            subject_raw_data[subject] = {"total": 0, "Correct": 0, "Wrong": 0, "Unattempted": 0}
        subject_raw_data[subject]["total"] += 1
        subject_raw_data[subject][status] += 1

    formatted_evaluation_data = []
    for subject, counts in subject_raw_data.items():
        attempted = counts["Correct"] + counts["Wrong"]
        accuracy = (counts["Correct"] / attempted * 100) if attempted > 0 else 0
        formatted_evaluation_data.append({
            "subject": subject, "total_questions": counts["total"], "correct": counts["Correct"],
            "wrong": counts["Wrong"], "unattempted": counts["Unattempted"], "accuracy": round(accuracy, 2)
        })

    prompt_text = SUBJECT_ANALYSIS_PROMPT.format(evaluation_data_json=json.dumps(formatted_evaluation_data, indent=2))
    messages = [SystemMessage(content="You are a subject-level performance analyst. Your response MUST be a JSON object as specified in the prompt."), HumanMessage(content=prompt_text)]
    response = model.invoke(messages)

    try:
        subject_analysis_result = json.loads(response.content)
        state["subject_performance"] = subject_analysis_result
    except json.JSONDecodeError:
        print(f"Error decoding JSON from SUBJECT_ANALYSIS_PROMPT response: {response.content}")
        state["subject_performance"] = {"error": "Failed to parse subject analysis", "raw_llm_response": response.content}
    print("--- Subject Analysis Node Completed ---")
    return state

def unattempted_analysis_node(state: AgentState) -> AgentState:
    print("\n--- Executing unattempted_analysis_node ---")
    unattempted_questions_eval = [
        q_eval for q_eval in state.get("evaluation_results", [])
        if q_eval["status"] == "Unattempted"
    ]

    unattempted_data_for_llm = []
    for q_eval in unattempted_questions_eval:
        q_orig = next((q for q in state["all_questions"] if q["id"] == q_eval["qid"]), None)
        if q_orig:
            unattempted_data_for_llm.append({
                "question_id": q_orig["id"],
                "question_text": q_orig["text"],
                "subject": q_orig.get("subject", "Unknown"),
            })
        else:
            print(f"Warning: Question with ID {q_eval['qid']} not found in all_questions")

    if not unattempted_data_for_llm:
        state["unattempted_reasons"] = {
            "individual_reasons": [],
            "overall_summary": "No questions were left unattempted."
        }
        print("--- Unattempted Analysis Node Completed: No unattempted questions ---")
        return state

    prompt_text = UNATTEMPTED_PROMPT.format(
        unattempted_questions_json=json.dumps(unattempted_data_for_llm, indent=2)
    )

    messages = [
        SystemMessage(content="You are an analyst. Your response MUST be a JSON object as specified in the prompt, with 'individual_reasons' (array of objects) and 'overall_summary' (string)."),
        HumanMessage(content=prompt_text)
    ]
    response = model.invoke(messages)

    try:
        unattempted_analysis_result = json.loads(response.content)
        if "individual_reasons" not in unattempted_analysis_result or "overall_summary" not in unattempted_analysis_result:
            raise ValueError("Response JSON missing required keys")
        state["unattempted_reasons"] = unattempted_analysis_result
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error decoding or validating JSON from UNATTEMPTED_PROMPT response:\n{response.content}\nError: {e}")
        state["unattempted_reasons"] = {
            "individual_reasons": [],
            "overall_summary": "Failed to parse unattempted analysis. Raw LLM response: " + response.content
        }

    print("--- Unattempted Analysis Node Completed ---")
    return state


def summary_report_node(state: AgentState) -> AgentState:
    """
    Generates a comprehensive summary report by leveraging an LLM with all gathered analysis data.
    """
    print("\n--- Executing summary_report_node ---")

    total_questions = len(state.get("all_questions", []))
    evaluated_results = state.get("evaluation_results", [])
    correct = sum(1 for r in evaluated_results if r["status"] == "Correct")
    wrong = sum(1 for r in evaluated_results if r["status"] == "Wrong")
    unattempted = sum(1 for r in evaluated_results if r["status"] == "Unattempted")
    attempted = correct + wrong

    subject_performance_data = state.get("subject_performance", {})
    mindset_insights_list = state.get("mindset_insights", [])
    unattempted_reasons_data = state.get("unattempted_reasons", {})
    references_list = state.get("references", [])

    serializable_mindset_insights = [insight.dict() if isinstance(insight, BaseModel) else insight for insight in mindset_insights_list]

    subject_performance_str = json.dumps(subject_performance_data, indent=2)
    mindset_insights_str = json.dumps(serializable_mindset_insights, indent=2)
    unattempted_reasons_str = json.dumps(unattempted_reasons_data, indent=2)
    references_str = json.dumps(references_list, indent=2)

    prompt_text = SUMMARY_PROMPT.format(
        total_questions=total_questions,
        attempted=attempted,
        correct=correct,
        wrong=wrong,
        unattempted=unattempted,
        subject_performance=subject_performance_str,
        mindset_insights=mindset_insights_str,
        unattempted_reasons=unattempted_reasons_str,
        references=references_str
    )

    messages = [
        SystemMessage(content="You are an expert UPSC exam analyst. Generate a comprehensive performance summary and an actionable plan based on the provided data and instructions. Ensure all requested sections are present and filled with content."),
        HumanMessage(content=prompt_text)
    ]

    try:
        response = model.invoke(messages)
        llm_generated_content = response.content
    except Exception as e:
        print(f"Error invoking LLM for summary report: {e}")
        llm_generated_content = "Error generating summary report from LLM."

    state["final_summary_report"] = llm_generated_content
    print("--- Summary Report Node Completed ---")
    return state

# --- Helper for serialization ---
def serialize_state(obj):
    if hasattr(obj, 'dict'): # Common for Pydantic models
        return obj.dict()
    elif hasattr(obj, 'to_dict'): # Custom to_dict method
        return obj.to_dict()
    elif isinstance(obj, list):
        return [serialize_state(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_state(value) for key, value in obj.items()}
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return {key: serialize_state(value) for key, value in obj.__dict__.items()}
    return obj