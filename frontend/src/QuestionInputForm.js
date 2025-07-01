import React from 'react';

function QuestionInputForm({ examQuestions, setExamQuestions, addQuestion, removeQuestion, fetchAnalysis, loading, error }) {

  const handleQuestionChange = (index, field, value) => {
    const updatedQuestions = [...examQuestions];
    if (field === 'options') {
      const optionsArray = value.split(',').map(pair => pair.trim().split(':'));
      updatedQuestions[index][field] = Object.fromEntries(optionsArray);
    } else {
      updatedQuestions[index][field] = value === '' ? null : value;
    }
    setExamQuestions(updatedQuestions);
  };

  return (
    <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-lg p-6 sm:p-8 mb-8">
      <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 mb-6 text-center">UPSC Exam Performance Analyzer</h1>
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Enter Exam Questions</h2>

      {examQuestions.map((question, index) => (
        <div key={question.id} className="border border-gray-300 rounded-lg p-4 mb-4 bg-gray-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-lg font-semibold text-gray-700">Question {index + 1} (ID: {question.id})</h3>
            <button
              onClick={() => removeQuestion(index)}
              className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded-md text-sm font-semibold"
            >
              Remove
            </button>
          </div>

          <div className="mb-3">
            <label className="block text-gray-700 text-sm font-bold mb-1">Question Text:</label>
            <textarea
              className="shadow border rounded w-full py-2 px-3 text-gray-700"
              value={question.text}
              onChange={(e) => handleQuestionChange(index, 'text', e.target.value)}
              rows="2"
            />
          </div>

          <div className="mb-3">
            <label className="block text-gray-700 text-sm font-bold mb-1">Options (A:Text, B:Text...):</label>
            <input
              type="text"
              className="shadow border rounded w-full py-2 px-3 text-gray-700"
              value={Object.entries(question.options).map(([key, val]) => `${key}:${val}`).join(', ')}
              onChange={(e) => handleQuestionChange(index, 'options', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-1">correct option:</label>
              <input
                type="text"
                className="shadow border rounded w-full py-2 px-3 text-gray-700"
                value={question.correct_option}
                onChange={(e) => handleQuestionChange(index, 'correct_option', e.target.value)}
              />
            </div>

            <div>
              <label className="block text-gray-700 text-sm font-bold mb-1">Your Answer:</label>
              <select
                className="shadow border rounded w-full py-2 px-3 text-gray-700"
                value={question.chosen_option ?? ''}
                onChange={(e) => handleQuestionChange(index, 'chosen_option', e.target.value)}
              >
                <option value="">Unattempted</option>
                <option value="A">A</option>
                <option value="B">B</option>
                <option value="C">C</option>
                <option value="D">D</option>
              </select>
            </div>
          </div>
        </div>
      ))}

      <div className="mb-6 text-center">
        <button
          onClick={addQuestion}
          className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-semibold mr-2"
        >
          Add New Question
        </button>
        <button
          onClick={fetchAnalysis}
          disabled={loading}
          className={`px-6 py-3 rounded-lg font-semibold text-white transition-all duration-300 ${
            loading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Analyzing...' : 'Generate Exam Report'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg mb-6">
          <strong className="font-bold">Error:</strong> <span>{error}</span>
        </div>
      )}
    </div>
  );
}

export default QuestionInputForm;
