import React, { useState } from "react";

export default function FormSelection({
  previewProducts,
  searchData,
  onFormSelect,
  onBack,
  loading,
  isTelegram,
}) {
  const [selectedForm, setSelectedForm] = useState("");

  // Защита от undefined
  const safePreviewProducts = previewProducts || [];

  // Группируем продукты по форме
  const groupedByForm = safePreviewProducts.reduce((acc, product) => {
  const key = product.form || "Без формы";

  if (!acc[key]) {
    acc[key] = {
      form: product.form,
      example: product,
      count: 1,
      minPrice: product.price,
      maxPrice: product.price,
      pharmacies: new Set([product.pharmacy_city]) // для подсчета уникальных аптек
    };
  } else {
    acc[key].count += 1;
    acc[key].minPrice = Math.min(acc[key].minPrice, product.price);
    acc[key].maxPrice = Math.max(acc[key].maxPrice, product.price);
    acc[key].pharmacies.add(product.pharmacy_city);
  }
  return acc;
}, {});

  // Преобразуем в массив
  const formGroups = Object.values(groupedByForm);

  const handleFormClick = (group) => {
  setSelectedForm(group.form);
  // Передаем только необходимые параметры
  onFormSelect(searchData.name, group.form);
};

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <div className="bg-white rounded-2xl shadow-sm border border-telegram-border overflow-hidden">
        {/* Header */}
        <div className="border-b border-telegram-border px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Выберите форму препарата
              </h2>
              <p className="text-gray-600 text-sm mt-1">
                для "
                <span className="font-semibold uppercase">
                  {searchData.name}
                </span>
                "{searchData.city && ` в городе ${searchData.city}`}
              </p>
            </div>
            <div className="flex gap-2">
              {/* Добавляем кнопку "Назад" для веб-версии */}
              {!isTelegram && (
                <button
                  onClick={onBack}
                  disabled={loading}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center text-sm"
                >
                  <svg
                    className="w-4 h-4 mr-2"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    />
                  </svg>
                  Назад
                </button>
              )}
              {/* Существующая кнопка "Новый поиск" */}
              <button
                onClick={onBack}
                disabled={loading}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors flex items-center text-sm"
              >
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                Новый поиск
              </button>
            </div>
          </div>
        </div>
        <div className="p-6">
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-800 mb-2">
              Выберите форму препарата:
            </h3>
            <p className="text-gray-600 text-sm">
              Нажмите на строку с нужной формой для просмотра результатов
            </p>
          </div>

          {/* Forms Table */}
          <div className="bg-gray-50 rounded-xl border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-100 border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Наименование
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Форма
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Производитель
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Страна
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">
                      Количество
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {formGroups.map((group, index) => (
                    <tr
                      key={index}
                      className={`hover:bg-telegram-primary hover:bg-opacity-5 transition-colors cursor-pointer ${
                        selectedForm === group.form
                          ? "bg-telegram-primary bg-opacity-10"
                          : ""
                      }`}
                      onClick={() => handleFormClick(group)}
                    >
                      <td className="py-3 px-4">
                        <div className="text-sm font-medium text-gray-800">
                          {searchData.name}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm text-gray-600">
                          {group.form}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm text-gray-600">
                          {group.example?.manufacturer || "Разные"}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm text-gray-600">
                          {group.example?.country || "Разные"}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm text-gray-600">
                          {group.count} вариантов
                        </div>
                        {loading && selectedForm === group.form && (
                          <div className="flex items-center mt-1">
                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-telegram-primary mr-2"></div>
                            <span className="text-xs text-gray-500">
                              Загрузка...
                            </span>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {formGroups.length === 0 && !loading && (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <svg
                  className="w-16 h-16 mx-auto"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-500 mb-2">
                Формы не найдены
              </h3>
              <p className="text-gray-400 text-sm mb-4">
                Попробуйте изменить параметры поиска
              </p>
              {/* Добавляем кнопку для возврата */}
              {!isTelegram && (
                <button
                  onClick={onBack}
                  className="bg-telegram-primary text-white font-medium py-2 px-6 rounded-lg transition-colors hover:bg-blue-600"
                >
                  Вернуться к поиску
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
