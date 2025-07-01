import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import QuestionInputForm from './QuestionInputForm';
import './App.css';

const dummyExamData = [
  {
    id: "1",
    text: "Which river is known as the 'Ganga of the South'?",
    options: { A: "Godavari", B: "Krishna", C: "Cauvery", D: "Narmada" },
    correct_option: "A",
    chosen_option: "A"
  },
  {
    id: "2",
    text: "Who founded the Mauryan Empire?",
    options: { A: "Ashoka", B: "Chandragupta Maurya", C: "Bindusara", D: "Samudragupta" },
    correct_option: "B",
    chosen_option: "A"
  },
  {
    id: "3",
    text: "What is the capital of Japan?",
    options: { A: "Seoul", B: "Beijing", C: "Tokyo", D: "Bangkok" },
    correct_option: "C",
    chosen_option: "C"
  },
  {
    id: "4",
    text: "Which of the following is a fundamental right in the Indian Constitution?",
    options: { A: "Right to Property", B: "Right to Education", C: "Right to Vote", D: "Right to Work" },
    correct_option: "B",
    chosen_option: null
  },
  {
    id: "5",
    text: "The Battle of Plassey was fought in which year?",
    options: { A: "1757", B: "1764", C: "1773", D: "1799" },
    correct_option: "A",
    chosen_option: "B"
  },
];

const generateUniqueId = () => `Q${Date.now().toString().slice(-6)}${Math.floor(Math.random() * 100)}`;

function App() {
  const [report, setReport] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [finalState, setFinalState] = useState(null);
  const [examQuestions, setExamQuestions] = useState(dummyExamData);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError('');
    setReport('');
    setFinalState(null);

    if (examQuestions.length === 0) {
      setError("Please add at least one question for analysis.");
      setLoading(false);
      return;
    }

    const sanitizedQuestions = examQuestions.map(q => ({
      ...q,
      chosen_option: ["A", "B", "C", "D"].includes(q.chosen_option) ? q.chosen_option : null
    }));

    try {
      const response = await fetch('http://localhost:5000/api/analyze_exam', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task: "Analyze UPSC Prelims performance based on the provided answers.",
          all_questions: sanitizedQuestions,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setReport(data.report);
      setFinalState(data.final_state);
    } catch (e) {
      console.error("Error fetching analysis:", e);
      setError(`Failed to fetch report: ${e.message}. Make sure your Flask backend is running.`);
    } finally {
      setLoading(false);
    }
  };

  const addQuestion = () => {
    setExamQuestions([
      ...examQuestions,
      {
        id: generateUniqueId(),
        text: "",
        options: { A: "", B: "", C: "", D: "" },
        correct_option: "",
        chosen_option: null
      }
    ]);
  };

  const removeQuestion = (index) => {
    const updatedQuestions = examQuestions.filter((_, i) => i !== index);
    setExamQuestions(updatedQuestions);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4 sm:p-6 lg:p-8 font-sans">
      <QuestionInputForm
        examQuestions={examQuestions}
        setExamQuestions={setExamQuestions}
        addQuestion={addQuestion}
        removeQuestion={removeQuestion}
        fetchAnalysis={fetchAnalysis}
        loading={loading}
        error={error}
      />
      {(report || finalState) && (
        <div className="mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200">
          {finalState && (
            <div className="markdown-body p-4 border border-gray-200 rounded-lg bg-white overflow-auto">
              <ReactMarkdown>{finalState}</ReactMarkdown>
            </div>
          )}
          {report && (
            <div className="mb-6">
              <h3 className="text-xl font-semibold text-gray-700 mb-3">Summary Report:</h3>
              <div className="markdown-body p-4 border border-gray-200 rounded-lg bg-white overflow-auto">
                <ReactMarkdown>{report}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
      {!report && !loading && !error && (
        <div className="mt-8 p-6 bg-blue-50 rounded-lg border border-blue-200 text-blue-700 text-center">
          Click "Generate Exam Report" to analyze the dummy UPSC exam data.
        </div>
      )}
    </div>
  );
}

export default App;
