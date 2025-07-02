# app.py
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, List

from graph import langgraph_app
from node import serialize_state # Assuming serialize_state is a helper for the graph
from report_formatter import format_final_state_for_display # Assuming this is an existing file
from models import AgentState # Import AgentState from models.py

app = Flask(__name__)
CORS(app) # Enable CORS for frontend communication

@app.route('/api/analyze_exam', methods=['POST'])
def analyze_exam():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data provided"}), 400

    task = data.get("task", "Analyze UPSC Prelims performance.")
    all_questions = data.get("all_questions", [])
    print("\n--- Received Exam Data for Analysis ---")
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
        "current_question_index": 0,
        "plan": "",
        "final_summary_report": ""
    }

    try:
        # LangGraph invocation
        final_state = langgraph_app.invoke(initial_state, {"configurable": {"thread_id": "1"}})
        print("\n--- LangGraph Analysis Completed ---")

        report_content = final_state.get("final_summary_report", "Analysis report could not be generated.")

        # Serialize the final state for display, if necessary
        serializable_final_state = serialize_state(final_state)
        final_content = format_final_state_for_display(serializable_final_state)

        print("\n--- Final Report Content Generated ---")
        print(final_content)
        return jsonify({
            "report": report_content,
            "final_state": final_content
        })
    except Exception as e:
        print(f"Error during LangGraph invocation: {e}")
        return jsonify({"error": f"An error occurred during analysis: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)