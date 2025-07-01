# app.py
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import TypedDict, List, Dict, Any, Optional

# LangChain and Pydantic imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic.v1 import BaseModel, Field # Using pydantic.v1
import json
import os
# LangGraph imports
from langgraph.graph import StateGraph, END
from report_formatter import format_final_state_for_display

# --- Environment Variable Setup ---
from dotenv import load_dotenv
load_dotenv()

# Initialize the LLM
# Consider setting temperature to a small non-zero value like 0.2 for creative summaries
model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.2)

# --- Define Pydantic Models ---
class QuestionEvaluation(BaseModel):
    qid: str
    status: str
    subject: str

class MindsetInsightDetail(BaseModel):
    question_id: str = Field(description="The ID of the question.")
    chosen_option_analysis: str = Field(description="Detailed analysis of why the student chose the incorrect option, including the likely thought process, common confusions, and specific conceptual gaps related to the correct answer.")
    depth_of_knowledge_assessment: str = Field(description="An assessment of the student's perceived depth of knowledge on the specific topic based on their answer, including what they might know, what they clearly misunderstand, and the nuances of their understanding of the underlying concepts.")
    distractor_analysis: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Analysis of each unchosen option (distractor), explaining its relevance to the topic or why it's incorrect, and what understanding of this distractor reveals about the student's broader knowledge. Keys are option labels (e.g., 'A', 'B', 'C', 'D')."
    )
    improvement_suggestion: str = Field(description="Specific actionable advice for the student to improve their understanding of this particular topic and related concepts, directly addressing the identified gaps.")

# --- AgentState ---
class AgentState(TypedDict):
    task: str
    current_question: Dict[str, Any]
    evaluation_results: List[Dict[str, Any]]
    mindset_insights: List[MindsetInsightDetail]
    subject_performance: Dict[str, Any]
    unattempted_reasons: Dict[str, Any]
    all_questions: List[Dict[str, Any]]
    references: List[str]
    current_question_index: int
    plan: str
    final_summary_report: str # This will hold the LLM's full generated report

# --- Prompts (Updated to the latest refined versions) ---
PLAN_PROMPT = """You are an expert exam analyst tasked with evaluating a student's UPSC Prelims performance. \ 
 Begin by outlining the overall approach you will take to analyze the student's answers. \ 
 Your outline should cover how you will classify responses (correct, wrong, unattempted), \ 
 how you will infer mindset for wrong answers, identify patterns in unattempted questions, \ 
 and how subject-wise performance will be measured. \ 
 Include any relevant notes or instructions that help guide this analysis process.""" 

EVALUATE_PROMPT = """You are an expert examiner tasked with classifying a student's answer to a UPSC Prelims multiple-choice question.
Given the question, the available options, and the correct answer,
determine whether the student's response is correct, wrong, or unattempted.

Return the evaluation in a structured JSON format with the following keys:
- "qid": Question ID
- "status": One of "Correct", "Wrong", or "Unattempted"
- "subject": The subject of the question (e.g., History, Polity, Economy, Geography, Environment, etc.)

Question ID: {question_id}
Question: {question_text}
Options:
A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}
Correct Option: {correct_option}
Chosen Option: {chosen_option}
"""

MINDSET_PROMPT = """You are a highly analytical cognitive expert tasked with deeply assessing a student's understanding when they answer a UPSC Prelims multiple-choice question incorrectly.

Given the question, all four options, the correct answer, and the student's incorrect choice, provide a comprehensive analysis. Your analysis should be diagnostic and reveal the nuances of the student's knowledge.

Question ID: {question_id}
Question: {question_text}
Options:
A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}
Correct Option: {correct_option}
Chosen Option (Incorrect): {chosen_option}
Subject: {subject}

Based on this information, provide a detailed analysis in JSON format, strictly adhering to the following structure for the `MindsetInsightDetail` Pydantic model. Ensure `distractor_analysis` provides an explanation for *each of the four options (A, B, C, D)*, indicating its relevance or why it's incorrect.

```json
{{
  "question_id": "The ID of the question.",
  "chosen_option_analysis": "Detailed analysis of why the student chose the incorrect option, including the likely thought process, common confusions, and specific conceptual gaps related to the correct answer.",
  "depth_of_knowledge_assessment": "An assessment of the student's perceived depth of knowledge on the specific topic based on their answer, including what they might know, what they clearly misunderstand, and the nuances of their understanding of the underlying concepts. Consider whether they have a superficial understanding or a fundamental misconception.",
  "distractor_analysis": {{
    "A": "Explanation for option A's relevance/incorrectness and what it implies about student knowledge. (e.g., 'This is the correct answer' or 'This is the chosen incorrect answer' or 'This distractor is plausible because X but incorrect because Y')",
    "B": "Explanation for option B's relevance/incorrectness and what it implies about student knowledge.",
    "C": "Explanation for option C's relevance/incorrectness and what it implies about student knowledge.",
    "D": "Explanation for option D's relevance/incorrectness and what it implies about student knowledge."
  }},
  "improvement_suggestion": "Specific actionable advice for the student to improve their understanding of this particular topic and related concepts, directly addressing the identified gaps."
}}
```
"""

SUBJECT_ANALYSIS_PROMPT = """You are a subject-level performance analyst reviewing a student's results from the UPSC Prelims exam. \ 
 You will be given a list of evaluated responses, each tagged with its subject and classified as 'Correct', 'Wrong', or 'Unattempted'. \ 
 Your task is to compute the student's performance for each subject. 

 For each subject: 
 - Count how many questions were asked. 
 - Count how many were correct, wrong, and unattempted. 
 - Calculate accuracy as: (correct / attempted) * 100. 
 - Identify weak subjects (low accuracy or many unattempted questions). 

 Return a summary that highlights: 
 - Strong subjects 
 - Weak subjects 
 - Any patterns in skipping or guessing behavior 

 This analysis will be used in the final report to provide actionable feedback to the student.

Here is the raw evaluation data for each question:
{evaluation_data_json}

Provide your analysis in a structured JSON format. **You MUST include both "overall_insights", "subject_breakdown", and "behavioral_patterns" keys.**
The "subject_breakdown" value MUST be a dictionary where keys are subject names and values are dictionaries with 'total_questions', 'correct', 'wrong', 'unattempted', 'accuracy', and 'status'.
Example JSON structure:
{{
    "overall_insights": "Student shows strong performance in X, but struggles in Y.",
    "subject_breakdown": {{
        "History": {{
            "total_questions": 10,
            "correct": 7,
            "wrong": 2,
            "unattempted": 1,
            "accuracy": 77.78,
            "status": "Strong"
        }},
        "Geography": {{
            "total_questions": 15,
            "correct": 5,
            "wrong": 8,
            "unattempted": 2,
            "accuracy": 38.46,
            "status": "Weak"
        }}
    }},
    "behavioral_patterns": "Tends to skip questions on economics."
}}
"""

UNATTEMPTED_PROMPT = """You are an analyst tasked with explaining why a student might skip certain UPSC prelims questions. \
Given a list of unattempted questions (including question ID, text, and subject), \
provide a short, concise reason for skipping for each question. \
Then, generate a brief summary covering common patterns or themes across all unattempted questions.

Return your analysis in a structured JSON object with the following keys:
- "individual_reasons": An array of objects, each with "question_id" and "reason_for_skipping".
- "overall_summary": A string providing the brief summary of patterns.

Unattempted Questions Data (JSON array):
{unattempted_questions_json}
"""

SUMMARY_PROMPT = """You are an expert UPSC exam analyst tasked with writing a comprehensive performance summary for a student based on detailed analysis data.

 You will be provided with:
 - Total number of questions
 - Number of attempted, correct, wrong, and unattempted questions
 - Subject-wise performance breakdown (accuracy and counts)
 - Detailed insights into why the student chose wrong answers (mindset analysis, including depth of knowledge and distractor analysis)
 - Possible reasons for unattempted questions
 - Additional relevant references or recent information (optional)

 Your task is to write a clear, motivating, and realistic summary report that includes:
 - A high-level overview of the student's performance
 - Strengths and subjects where the student excelled
 - Weaknesses and subjects needing improvement
 - Behavioral patterns noticed (e.g., tendency to skip certain topics, common misconceptions)
 - Suggestions for focused study and improvement strategies
 - If available, include up-to-date relevant references or resources to support the student’s preparation
- **FINALLY, A CRUCIAL 'Actionable Plan for Next Time' section.** This final section is paramount. It MUST be detailed and provide clear guidance on areas like conceptual clarity, revision techniques, time management, and subject-specific focus.
 Write the full summary below in an encouraging tone suitable for a UPSC aspirant.

## Overall Performance Summary:
Based on the provided data, here is a comprehensive analysis of the student's performance in the UPSC Prelims exam.

[GENERATED OVERVIEW CONTENT HERE - LLM WILL FILL THIS]

---

 Here is the detailed data for your analysis:

 Total Questions: {total_questions}
 Attempted: {attempted}
 Correct: {correct}
 Wrong: {wrong}
 Unattempted: {unattempted}

 Subject-wise Performance:
 {subject_performance}

 Mindset Insights on Wrong Answers:
 {mindset_insights}

 Unattempted Questions Analysis:
 {unattempted_reasons}

 Additional References:
 {references}

## Actionable Plan for Next Time:
**Based on ALL the preceding analysis and data, provide a comprehensive, specific, and actionable set of recommendations for the student's future preparation. This section is the most important part of the report for the student's improvement. It MUST be detailed and provide clear guidance on areas like conceptual clarity, revision techniques, time management, and subject-specific focus.**
"""
# --- End of Prompts ---

# --- Node Definitions ---
def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ]
    response = model.invoke(messages)
    return {"plan": response.content}

def evaluate_node(state: AgentState) -> AgentState:
    if state["current_question_index"] >= len(state["all_questions"]):
        return state

    current_q_data = state["all_questions"][state["current_question_index"]]
    state["current_question"] = current_q_data

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
    )

    try:
        evaluation_result_obj = structured_llm_evaluator.invoke([HumanMessage(content=prompt_text)])
        evaluation_result_dict = evaluation_result_obj.dict()

        # Ensure 'subject' field is present and valid, else extract from question
        subject = evaluation_result_dict.get("subject")
        if not subject:
            subject = extract_subject_from_question(current_q_data["text"])
            evaluation_result_dict["subject"] = subject

        if "evaluation_results" not in state:
            state["evaluation_results"] = []
        state["evaluation_results"].append(evaluation_result_dict)

    except Exception as e:
        print(f"❌ Error during evaluation_node: {e}")
        print(f"Prompt used:\n{prompt_text}")
        # Fallback: extract subject from question text
        subject = extract_subject_from_question(current_q_data["text"])
        state["evaluation_results"].append({
            "qid": current_q_data["id"],
            "status": "Unknown",
            "subject": subject if subject else "General",
            "error": str(e)
        })

    state["current_question_index"] += 1
    print("\n--- Evaluation Node Completed ---")
    return state


def extract_subject_from_question(question_text: str) -> str:
    question_text_lower = question_text.lower()

    # Simple keyword-to-subject mapping
    subject_keywords = {
        "geography": ["river", "mountain", "lake", "continent", "ocean", "climate", "geography", "location"],
        "history": ["empire", "battle", "king", "queen", "revolution", "ancient", "medieval", "history"],
        "polity": ["constitution", "right", "vote", "parliament", "law", "government", "amendment", "polity"],
        "economics": ["economy", "inflation", "budget", "tax", "finance", "market", "trade", "economic"],
        "science": ["physics", "chemistry", "biology", "experiment", "energy", "cell", "force", "scientific", "science"],
        "environment": ["climate", "pollution", "environment", "ecosystem", "biodiversity", "conservation"],
        # Add more subjects and keywords as needed
    }

    for subject, keywords in subject_keywords.items():
        if any(keyword in question_text_lower for keyword in keywords):
            return subject.capitalize()

    # Default fallback
    return "General"


def mindset_inference_node(state: AgentState) -> AgentState:
    print("\n--- Executing mindset_inference_node ---")
    
    # Track questions already analyzed for mindset
    current_mindset_qids = {insight.question_id for insight in state.get("mindset_insights", [])}
    wrong_questions_for_mindset = []

    # Filter wrong answers that haven't been analyzed yet
    for q_eval in state.get("evaluation_results", []):
        if q_eval["status"] == "Wrong" and q_eval["qid"] not in current_mindset_qids:
            q_orig = next((q for q in state["all_questions"] if q["id"] == q_eval["qid"]), None)
            required_keys = ["id", "text", "options", "correct_option", "chosen_option"]
            if q_orig and all(k in q_orig for k in required_keys):
                wrong_questions_for_mindset.append(q_orig)
            else:
                print(f"⚠️ Skipping malformed question for mindset analysis: {q_orig}")

    # Initialize list if not already
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

        except Exception as e:
            print(f"❌ Error generating mindset insight for QID={q_data['id']}: {e}")
            continue

    print("\n--- Mindset Inference Node Completed ---")
    return state

def subject_analysis_node(state: AgentState) -> AgentState:
    
    evaluated_data = state.get("evaluation_results", [])
    if not evaluated_data:
        state["subject_performance"] = {"error": "No evaluation data available."}
        return state

    subject_raw_data = {}
    for eval_item in evaluated_data:
        subject = eval_item["subject"]
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
    print("\n--- Subject Analysis Node Completed ---")
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
        print("\n--- Unattempted Analysis Node Completed: No unattempted questions ---")
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
        # Minimal validation
        if "individual_reasons" not in unattempted_analysis_result or "overall_summary" not in unattempted_analysis_result:
            raise ValueError("Response JSON missing required keys")
        state["unattempted_reasons"] = unattempted_analysis_result
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error decoding or validating JSON from UNATTEMPTED_PROMPT response:\n{response.content}\nError: {e}")
        state["unattempted_reasons"] = {
            "individual_reasons": [],
            "overall_summary": "Failed to parse unattempted analysis. Raw LLM response: " + response.content
        }

    print("\n--- Unattempted Analysis Node Completed ---")
    return state


def summary_report_node(state: AgentState) -> AgentState:
    """
    Generates a comprehensive summary report by leveraging an LLM with all gathered analysis data.
    """
    print("\n--- Executing summary_report_node ---")

    # 1. Prepare data for the LLM prompt
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

    # 2. Format the SUMMARY_PROMPT with all collected data
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

    # 3. Construct messages for the LLM
    messages = [
        SystemMessage(content="You are an expert UPSC exam analyst. Generate a comprehensive performance summary and an actionable plan based on the provided data and instructions. Ensure all requested sections are present and filled with content."),
        HumanMessage(content=prompt_text)
    ]

    # 4. Invoke the LLM
    try:
        response = model.invoke(messages)
        llm_generated_content = response.content
    except Exception as e:
        print(f"Error invoking LLM for summary report: {e}")
        llm_generated_content = "Error generating summary report from LLM."

    # 5. Store the LLM's full generated content in the state
    state["final_summary_report"] = llm_generated_content
    print("\n--- Summary Report Node Completed ---")
    return state

# --- Conditional Edges ---
def should_continue_evaluating(state: AgentState) -> str:
    if state["current_question_index"] < len(state["all_questions"]):
        return "continue_evaluation"
    else:
        return "evaluation_complete"

# --- Building the LangGraph ---
app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

# Initialize LangGraph pipeline once
workflow = StateGraph(AgentState)
workflow.add_node("planner", plan_node)
workflow.add_node("evaluate_question", evaluate_node)
workflow.add_node("mindset_inference", mindset_inference_node)
workflow.add_node("subject_analysis", subject_analysis_node)
workflow.add_node("unattempted_analysis", unattempted_analysis_node) 
workflow.add_node("summary_report", summary_report_node)

workflow.set_entry_point("planner")
workflow.add_edge("planner", "evaluate_question")
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

langgraph_app = workflow.compile() # Renamed to avoid conflict with Flask 'app'
def serialize_state(obj):
    if hasattr(obj, 'dict'): # Common for Pydantic models
        return obj.dict()
    elif hasattr(obj, 'to_dict'): # Custom to_dict method
        return obj.to_dict()
    elif isinstance(obj, list):
        return [serialize_state(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_state(value) for key, value in obj.items()}
    # NEW: Handle general custom objects by converting their __dict__ to a dictionary
    # This will catch classes like MindsetInsightDetail if they are not Pydantic models
    # and hold their data in attributes accessible via __dict__.
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return {key: serialize_state(value) for key, value in obj.__dict__.items()}
    return obj

@app.route('/api/analyze_exam', methods=['POST'])
def analyze_exam():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data provided"}), 400

    task = data.get("task", "Analyze UPSC Prelims performance.")
    all_questions = data.get("all_questions", [])
    print("\n--- Received Exam Data for Analysis ---")
    #print(all_questions)
    if not all_questions:
        return jsonify({"error": "No exam questions provided for analysis."}), 400
   
    initial_state: AgentState = {
        "task": task,
        "all_questions": all_questions,
        "current_question": {},
        "evaluation_results": [],
        "mindset_insights": [],
        "subject_performance": {},
        "unattempted_reasons": {},
        "references": [],
        "current_question_index": 0
    }

    try:
        final_state = langgraph_app.invoke(initial_state, {"configurable": {"thread_id": "1"}})
        print("\n--- LangGraph Analysis Completed ---")
        # The final_summary_report contains the LLM-generated Markdown string
        report_content = final_state.get("final_summary_report", "Analysis report could not be generated.")
        serializable_final_state = serialize_state(final_state)
        final_content = format_final_state_for_display(serializable_final_state)
        print("\n--- Final Report Content Generated ---")
        print(final_content)  # For debugging, you can remove this in production
        return jsonify({
            "report": report_content,
            "final_state": final_content# Sending the entire final_state object
        })
    except Exception as e:
        print(f"Error during LangGraph invocation: {e}")
        return jsonify({"error": f"An error occurred during analysis: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True) # debug=True for development, set to False for production
