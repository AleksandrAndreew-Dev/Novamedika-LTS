import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import Toast from "./Toast";

export default function AskPharmacist({ onClose }) {
  const navigate = useNavigate();
  const [questionText, setQuestionText] = useState("");
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [toast, setToast] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!questionText.trim()) return;

    try {
      setSending(true);

      // Генерируем или получаем anon_user_id из localStorage
      let anonUserId = localStorage.getItem("anon_user_id");
      if (!anonUserId) {
        anonUserId = crypto.randomUUID
          ? crypto.randomUUID()
          : "anon-" + Date.now() + "-" + Math.random().toString(36).slice(2);
        localStorage.setItem("anon_user_id", anonUserId);
      }

      const response = await api.post(
        "/api/public/questions/",
        {
          text: questionText.trim(),
          category: "general",
          anon_user_id: anonUserId,
        },
        {
          headers: { "X-API-KEY": import.meta.env.VITE_API_KEY || "" },
        },
      );

      const data = response.data;
      setResult({
        uuid: data.uuid,
        text: data.text,
      });

      setToast({ message: "✅ Вопрос отправлен фармацевту", type: "success" });

      // Сохраняем в localStorage историю вопросов
      const history = JSON.parse(
        localStorage.getItem("anon_questions") || "[]",
      );
      history.push({
        uuid: data.uuid,
        text: data.text,
        created_at: new Date().toISOString(),
      });
      localStorage.setItem("anon_questions", JSON.stringify(history));
    } catch (err) {
      console.error("[AskPharmacist] Failed:", err);
      setToast({
        message: "Ошибка отправки вопроса. Попробуйте позже.",
        type: "error",
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50"
        onClick={onClose}
      >
        <div
          className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 relative"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
            aria-label="Закрыть"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>

          {/* Icon */}
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="w-7 h-7 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
          </div>

          {result ? (
            /* Success state */
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Вопрос отправлен!
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Фармацевт ответит в ближайшее время.
              </p>
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => {
                    onClose();
                    navigate(`/chat/${result.uuid}`);
                  }}
                  className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium py-2.5 px-6 rounded-full transition-all text-sm"
                >
                  💬 Перейти в чат
                </button>
                <button
                  onClick={() => {
                    setResult(null);
                    setQuestionText("");
                  }}
                  className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-6 rounded-full transition-colors text-sm"
                >
                  Задать ещё вопрос
                </button>
              </div>
            </div>
          ) : (
            /* Form state */
            <>
              <h3 className="text-lg font-semibold text-gray-900 text-center mb-1">
                Задать вопрос фармацевту
              </h3>
              <p className="text-sm text-gray-500 text-center mb-5">
                Опишите ваш вопрос, и фармацевт ответит вам
              </p>

              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <textarea
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    placeholder="Например: есть ли в наличии Цитрамон, какие есть аналоги?"
                    rows={4}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-2xl text-sm resize-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition-all text-gray-900 placeholder:text-gray-400"
                    style={{ fontFamily: "inherit" }}
                  />
                  <p className="text-xs text-gray-400 mt-1 text-right">
                    {questionText.length}/500
                  </p>
                </div>

                <button
                  type="submit"
                  disabled={sending || !questionText.trim()}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium rounded-2xl transition-colors text-sm"
                >
                  {sending ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg
                        className="animate-spin h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        ></path>
                      </svg>
                      Отправка...
                    </span>
                  ) : (
                    "Отправить вопрос"
                  )}
                </button>
              </form>

              <p className="text-xs text-gray-400 text-center mt-4">
                Нажимая "Отправить", вы соглашаетесь с обработкой данных
                согласно{" "}
                <a
                  href="/privacy-policy"
                  target="_blank"
                  className="text-blue-500 underline"
                >
                  Политике конфиденциальности
                </a>
              </p>
            </>
          )}
        </div>
      </div>

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
          duration={3000}
        />
      )}
    </>
  );
}
