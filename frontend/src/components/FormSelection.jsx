// components/FormSelection.jsx
import React, { useState } from "react";

export default function FormSelection({
  availableForms,
  previewProducts,
  totalFound,
  searchData,
  onFormSelect,
  onBack,
  loading
}) {
  const [selectedForm, setSelectedForm] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedForm) {
      alert("Пожалуйста, выберите форму препарата");
      return;
    }
    onFormSelect(selectedForm);
  };

  return (
    <div className="results container-lg">
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <h4 className="results-text mb-0">
            Найдено {totalFound} вариантов для "{searchData.name}"
            {searchData.city && ` в городе ${searchData.city}`}
          </h4>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onBack}
            disabled={loading}
          >
            ← Новый поиск
          </button>
        </div>

        <div className="card-body">
          <div className="row">
            <div className="col-md-4">
              <h5>Выберите форму препарата:</h5>
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <select
                    className="form-select"
                    value={selectedForm}
                    onChange={(e) => setSelectedForm(e.target.value)}
                    required
                  >
                    <option value="">Выберите форму...</option>
                    {availableForms.map((form) => (
                      <option key={form} value={form}>
                        {form}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading || !selectedForm}
                >
                  {loading ? "Загрузка..." : "Показать результаты"}
                </button>
              </form>
            </div>

            <div className="col-md-8">
              <h5>Примеры найденных препаратов:</h5>
              <div className="table-responsive">
                <table className="table table-sm table-hover">
                  <thead>
                    <tr>
                      <th>Название</th>
                      <th>Форма</th>
                      <th>Производитель</th>
                      <th>Цена</th>
                      <th>Город</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewProducts.map((product, index) => (
                      <tr key={index}>
                        <td>{product.name}</td>
                        <td>{product.form}</td>
                        <td>{product.manufacturer}</td>
                        <td>{product.price} Br</td>
                        <td>{product.pharmacy_city}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
