import React, { useState } from "react";
import { useAuth } from "./hooks/useAuth";
import DashboardStats from "./components/dashboard/DashboardStats";
import QuestionsList from "./components/consultations/QuestionsList";
import ConsultationChat from "./components/consultations/ConsultationChat";
import MainLayout from "./components/layout/MainLayout";

const filterOptions = [
  { key: "new", label: "Новые" },
  { key: "in_progress", label: "В работе" },
  { key: "completed", label: "Завершенные" },
  { key: "all", label: "Все" },
];

export default function PharmacistContent() {
  const { isAuthenticated, user, loading } = useAuth();
  const [filter, setFilter] = useState("new");
  const [selectedQuestionId, setSelectedQuestionId] = useState(null);

  if (!loading && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">
            Требуется авторизация. Перенаправление...
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка панели...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-yellow-100 rounded-full flex items-center justify-center mb-4">
            <svg
              className="h-8 w-8 text-yellow-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <p className="text-gray-600">Ошибка загрузки данных пользователя</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Обновить страницу
          </button>
        </div>
      </div>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-8">
        <section className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
          <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-sm text-gray-500">Добро пожаловать,</p>
                <h1 className="text-3xl font-bold text-gray-900">
                  {user?.user?.first_name || user?.name || "Фармацевт"}
                </h1>
                <p className="mt-1 text-gray-600 max-w-2xl">
                  Сократите время ответа и решайте новые консультации в один
                  клик.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-green-200 bg-green-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-green-700">
                    Статус
                  </p>
                  <p className="mt-2 text-lg font-semibold text-green-900">
                    {user?.is_online ? "🟢 Онлайн" : "⚫ Офлайн"}
                  </p>
                </div>
                <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
                    Аптека
                  </p>
                  <p className="mt-2 text-lg font-semibold text-blue-900">
                    {user?.pharmacy_info?.name || "Не указано"}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setFilter("new")}
                className={`rounded-3xl px-5 py-4 text-left transition-shadow ${filter === "new" ? "shadow-lg border border-blue-300 bg-blue-50" : "border border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50"}`}
              >
                <p className="text-sm text-gray-500">Срочные</p>
                <p className="mt-2 text-lg font-semibold text-gray-900">
                  Новые вопросы
                </p>
              </button>
              <button
                type="button"
                onClick={() => setFilter("in_progress")}
                className={`rounded-3xl px-5 py-4 text-left transition-shadow ${filter === "in_progress" ? "shadow-lg border border-blue-300 bg-blue-50" : "border border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50"}`}
              >
                <p className="text-sm text-gray-500">В работе</p>
                <p className="mt-2 text-lg font-semibold text-gray-900">
                  Текущие консультации
                </p>
              </button>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">
                Быстрый обзор
              </h2>
              <div className="mt-5 grid gap-4">
                <div className="rounded-3xl bg-blue-600 p-4 text-white">
                  <p className="text-sm uppercase tracking-wide text-blue-100">
                    Задача
                  </p>
                  <p className="mt-2 text-lg font-semibold">
                    Ответьте первому вопросу в списке
                  </p>
                </div>
                <div className="rounded-3xl border border-gray-200 p-4">
                  <p className="text-sm text-gray-500">Профиль</p>
                  <p className="mt-2 font-semibold text-gray-900">
                    {user?.user?.first_name || user?.name || "—"}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {user?.user?.telegram_id || "Telegram ID не указан"}
                  </p>
                </div>
                <div className="rounded-3xl border border-gray-200 p-4">
                  <p className="text-sm text-gray-500">Аптека</p>
                  <p className="mt-2 font-semibold text-gray-900">
                    {user?.pharmacy_info?.name || "—"}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {user?.pharmacy_info?.chain || ""}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">Действие</h2>
              <p className="mt-2 text-gray-600">
                Выберите вопрос и сразу начните диалог в правой панели.
              </p>
              <button
                type="button"
                onClick={() => setSelectedQuestionId(null)}
                className="mt-4 w-full rounded-3xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Сбросить выбор
              </button>
            </div>
          </aside>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.65fr_1.35fr]">
          <div className="space-y-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900">
                  Вопросы
                </h2>
                <p className="mt-1 text-gray-600">
                  Фильтр:{" "}
                  {filterOptions.find((item) => item.key === filter)?.label}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {filterOptions.map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setFilter(item.key)}
                    className={`rounded-full px-4 py-2 text-sm font-semibold transition ${filter === item.key ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <QuestionsList
              filter={filter}
              selectedQuestionId={selectedQuestionId}
              onSelectQuestion={setSelectedQuestionId}
            />
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">
                Статистика
              </h2>
              <div className="mt-4">
                <DashboardStats />
              </div>
            </div>

            <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm min-h-[32rem]">
              <h2 className="text-lg font-semibold text-gray-900">Диалог</h2>
              <p className="mt-2 text-gray-600">
                Выберите вопрос слева, чтобы ответить без лишних переходов.
              </p>
              <div className="mt-5 h-[calc(100%-5rem)]">
                <ConsultationChat
                  questionId={selectedQuestionId}
                  onClose={() => setSelectedQuestionId(null)}
                />
              </div>
            </div>
          </div>
        </section>
      </div>
    </MainLayout>
  );
}
