// components/SearchResults.jsx
import React from "react";

export default function SearchResults({
  results,
  searchData,
  pagination,
  onPageChange,
  onNewSearch,
  loading
}) {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} мин назад`;
    } else if (diffHours < 24) {
      return `${diffHours} ч назад`;
    } else {
      return `${diffDays} дн назад`;
    }
  };

  return (
    <div className="results container-lg">
      <div className="card">
        <div className="card-header d-flex justify-content-between align-items-center">
          <div>
            <h5 className="results-text">Результаты поиска: </h5>
            <span className="results-text2">
              {searchData.name} {searchData.form}
              {results[0] && ` - ${results[0].manufacturer} ${results[0].country}`}
            </span>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onNewSearch}
            disabled={loading}
          >
            ← Новый поиск
          </button>
        </div>

        <div className="card-body">
          {results.length === 0 ? (
            <div className="text-center py-4">
              <h5>Ничего не найдено</h5>
              <p>Попробуйте изменить параметры поиска</p>
            </div>
          ) : (
            <>
              <div className="table-responsive">
                <table id="results-table" className="table-sm table-light-active align-middle">
                  <thead>
                    <tr className="table-light">
                      <th scope="col">Аптека</th>
                      <th scope="col">Город</th>
                      <th scope="col">Адрес</th>
                      <th scope="col">Телефон</th>
                      <th scope="col">Название</th>
                      <th scope="col">Форма</th>
                      <th scope="col">Цена в аптеке бел.руб</th>
                      <th scope="col">Количество в Аптеке</th>
                      <th scope="col">Производитель, Страна</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((item, index) => (
                      <tr key={index} className="table-light">
                        <td className="table-light">
                          {item.pharmacy_name} №{item.pharmacy_number}
                          <br />
                          <small className="updated-time text-muted">
                            Обновлено: {formatDate(item.updated_at)}
                          </small>
                        </td>
                        <td className="table-light">{item.pharmacy_city}</td>
                        <td className="table-light">{item.pharmacy_address}</td>
                        <td className="table-light">{item.pharmacy_phone}</td>
                        <td className="table-light">{item.name}</td>
                        <td className="table-light">{item.form}</td>
                        <td className="table-light">
                          <span className="pharma-price">{item.price} Br</span>
                        </td>
                        <td className="table-light">
                          {item.quantity} уп.
                          <br />
                          <small className="text-muted">Уточняйте кол-во в аптеке</small>
                        </td>
                        <td className="table-light">
                          {item.manufacturer}, {item.country}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Пагинация */}
              {pagination.totalPages > 1 && (
                <nav aria-label="Page navigation" className="mt-3">
                  <ul className="pagination justify-content-center">
                    <li className={`page-item ${pagination.page === 1 ? 'disabled' : ''}`}>
                      <button
                        className="page-link"
                        onClick={() => onPageChange(pagination.page - 1)}
                        disabled={pagination.page === 1 || loading}
                      >
                        Назад
                      </button>
                    </li>

                    {[...Array(pagination.totalPages)].map((_, index) => {
                      const pageNum = index + 1;
                      return (
                        <li
                          key={pageNum}
                          className={`page-item ${pagination.page === pageNum ? 'active' : ''}`}
                        >
                          <button
                            className="page-link"
                            onClick={() => onPageChange(pageNum)}
                            disabled={loading}
                          >
                            {pageNum}
                          </button>
                        </li>
                      );
                    })}

                    <li className={`page-item ${pagination.page === pagination.totalPages ? 'disabled' : ''}`}>
                      <button
                        className="page-link"
                        onClick={() => onPageChange(pagination.page + 1)}
                        disabled={pagination.page === pagination.totalPages || loading}
                      >
                        Вперед
                      </button>
                    </li>
                  </ul>
                </nav>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
