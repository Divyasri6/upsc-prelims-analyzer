# models.py
from typing import TypedDict, List, Dict, Any, Optional
from pydantic.v1 import BaseModel, Field

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