import React, { useState, useEffect } from 'react';

export default function PharmacistDashboard() {
  const [questions, setQuestions] = useState([]);
  const [selectedQuestion, setSelectedQuestion] = useState(null);

  // Загрузка вопросов, ответы и т.д.

  return (
    <div className="p-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Список вопросов */}
        <div className="lg:col-span-1">
          <h2 className="text-xl font-bold mb-4">Вопросы</h2>
          <div className="space-y-3">
            {questions.map(question => (
              <QuestionCard
                key={question.uuid}
                question={question}
                onSelect={setSelectedQuestion}
              />
            ))}
          </div>
        </div>

        {/* Область ответа */}
        <div className="lg:col-span-2">
          {selectedQuestion && (
            <AnswerArea
              question={selectedQuestion}
              onAnswer={handleAnswer}
            />
          )}
        </div>
      </div>
    </div>
  );
}
