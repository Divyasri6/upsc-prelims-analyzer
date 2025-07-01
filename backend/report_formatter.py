from typing import Any, Dict, List

def format_final_state_for_display(result: Dict[str, Any]) -> str:
    """
    Formats the final_state dictionary (which is 'result' here) into a readable Markdown string for display.
    """
    markdown_output = []

    markdown_output.append("# UPSC Exam Performance Analysis Report\n")
    markdown_output.append("\n---\n")

    # 1. Key Metrics - Directly extracted from evaluation_results
    markdown_output.append("## Key Performance Metrics\n")
    total_questions = len(result.get("all_questions", []))
    evaluated_results = result.get("evaluation_results", [])
    correct_count = sum(1 for r in evaluated_results if r.get("status") == "Correct")
    wrong_count = sum(1 for r in evaluated_results if r.get("status") == "Wrong")
    unattempted_count = sum(1 for r in evaluated_results if r.get("status") == "Unattempted")
    attempted_count = correct_count + wrong_count

    markdown_output.append(f"- **Total Questions:** {total_questions}")
    markdown_output.append(f"- **Attempted:** {attempted_count}")
    markdown_output.append(f"- **Correct:** {correct_count}")
    markdown_output.append(f"- **Wrong:** {wrong_count}")
    markdown_output.append(f"- **Unattempted:** {unattempted_count}\n")
    markdown_output.append("\n---\n")

    # 2. Subject-wise Performance
    markdown_output.append("## Subject-wise Performance Breakdown\n")
    subject_performance = result.get("subject_performance", {})
    if subject_performance:
        markdown_output.append(f"**Overall Subject Insights:** {subject_performance.get('overall_insights', 'N/A')}\n")
        markdown_output.append("### Detailed Subject Breakdown\n")
        for subject, data in subject_performance.get("subject_breakdown", {}).items():
            markdown_output.append(f"#### {subject}\n")
            markdown_output.append(f"- Total Questions: {data.get('total_questions', 'N/A')}")
            markdown_output.append(f"- Correct: {data.get('correct', 'N/A')}")
            markdown_output.append(f"- Wrong: {data.get('wrong', 'N/A')}")
            markdown_output.append(f"- Unattempted: {data.get('unattempted', 'N/A')}")
            markdown_output.append(f"- Accuracy: {data.get('accuracy', 'N/A')}%")
            markdown_output.append(f"- Status: **{data.get('status', 'N/A')}**\n")

        markdown_output.append(f"**Behavioral Patterns across Subjects:** {subject_performance.get('behavioral_patterns', 'N/A')}\n")
    else:
        markdown_output.append("No subject performance data available.\n")
    markdown_output.append("\n---\n")

    # 3. Detailed Mindset Insights (Wrong Answers)
    markdown_output.append("## Detailed Mindset Insights (Wrong Answers)\n")
    mindset_insights = result.get("mindset_insights", [])
    if mindset_insights:
        for i, insight in enumerate(mindset_insights):
            # Assuming insights are now dictionaries after serialization
            question_id = insight.get("question_id", "N/A")
            chosen_option_analysis = insight.get("chosen_option_analysis", "N/A")
            depth_of_knowledge_assessment = insight.get("depth_of_knowledge_assessment", "N/A")
            distractor_analysis = insight.get("distractor_analysis", {})
            improvement_suggestion = insight.get("improvement_suggestion", "N/A")

            markdown_output.append(f"### Question ID: {question_id}\n")
            markdown_output.append(f"- **Chosen Option Analysis:** {chosen_option_analysis}\n")
            markdown_output.append(f"- **Depth of Knowledge Assessment:** {depth_of_knowledge_assessment}\n")

            if distractor_analysis:
                markdown_output.append("- **Distractor Analysis:**\n")
                for opt in sorted(distractor_analysis.keys()):
                    analysis = distractor_analysis[opt]
                    markdown_output.append(f"  - **Option {opt}:** {analysis}\n")

            markdown_output.append(f"- **Improvement Suggestion:** {improvement_suggestion}\n")
            if i < len(mindset_insights) - 1:
                markdown_output.append("---\n")
    else:
        markdown_output.append("No specific mindset insights for wrong answers.\n")
    markdown_output.append("\n---\n")

    # 4. Unattempted Questions Analysis
    markdown_output.append("## Unattempted Questions Analysis\n")
    unattempted_reasons = result.get("unattempted_reasons", {})
    if unattempted_reasons:
        markdown_output.append(f"**Overall Summary:** {unattempted_reasons.get('overall_summary', 'N/A')}\n")
        individual_reasons = unattempted_reasons.get("individual_reasons", [])
        if individual_reasons:
            markdown_output.append("### Individual Reasons for Skipping:\n")
            for reason in individual_reasons:
                markdown_output.append(f"- **QID {reason.get('question_id', 'N/A')}:** {reason.get('reason_for_skipping', 'N/A')}\n")
    else:
        markdown_output.append("No unattempted questions analysis available.\n")
    markdown_output.append("\n---\n")
    
    # 5. Additional References (if any)
    references = result.get("references", [])
    if references:
        markdown_output.append("## Additional References\n")
        for ref in references:
            markdown_output.append(f"- {ref}\n")
    else:
        markdown_output.append("No additional references provided.\n")
    markdown_output.append("\n---\n")

    return "".join(markdown_output)

if __name__ == "__main__":
    # Example usage for testing the function within this file
    # This 'result' dictionary should mimic the structure of your `final_state`
    # after it has been serialized (e.g., Pydantic models converted to dicts).
    sample_result = {
        "all_questions": [{"id": "Q001"}, {"id": "Q002"}, {"id": "Q003"}],
        "evaluation_results": [
            {"status": "Correct", "question_id": "Q001"},
            {"status": "Wrong", "question_id": "Q002"},
            {"status": "Unattempted", "question_id": "Q003"}
        ],
        "subject_performance": {
            "overall_insights": "Good start.",
            "subject_breakdown": {
                "History": {"total_questions": 1, "correct": 0, "wrong": 1, "unattempted": 0, "accuracy": 0.0, "status": "Needs Work"},
                "Geography": {"total_questions": 1, "correct": 1, "wrong": 0, "unattempted": 0, "accuracy": 100.0, "status": "Excellent"}
            },
            "behavioral_patterns": "Attempts known subjects first."
        },
        "mindset_insights": [
            {
                "question_id": "Q002",
                "chosen_option_analysis": "Confused dates.",
                "depth_of_knowledge_assessment": "Superficial.",
                "distractor_analysis": {"A": "Distractor A analysis."},
                "improvement_suggestion": "Study timelines."
            }
        ],
        "unattempted_reasons": {
            "overall_summary": "One question skipped.",
            "individual_reasons": [
                {"question_id": "Q003", "reason_for_skipping": "Time constraint."}
            ]
        },
        "references": ["Book X", "Book Y"]
    }
    formatted_output = format_final_state_for_display(sample_result)