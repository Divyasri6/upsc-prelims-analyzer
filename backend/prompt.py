# --- Prompts (Updated to the latest refined versions) ---
PLAN_PROMPT = """You are an expert exam analyst tasked with evaluating a student's UPSC Prelims performance. \ 
 Begin by outlining the overall approach you will take to analyze the student's answers. \ 
 Your outline should cover how you will classify responses (correct, wrong, unattempted), \ 
 how you will infer mindset for wrong answers, identify patterns in unattempted questions, \ 
 and how subject-wise performance will be measured. \ 
 Include any relevant notes or instructions that help guide this analysis process.""" 

LLM_SUBJECT_PROMPT = """You are a subject classification expert for UPSC prelims questions.
Given a multiple-choice question, identify the most relevant subject it belongs to.

Subjects can include: History, Polity, Geography, Economy, Environment, Science & Tech, General Knowledge, or Current Affairs.

Question:
"{question_text}"

Return the subject as a **single word string**, e.g., "History", "Polity", "Environment", etc.
"""


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
