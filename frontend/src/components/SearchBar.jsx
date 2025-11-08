import React, { useState } from "react";

// Исправляем импорты изображений
import leftLeaf from "../assets/left-list.png";
import rightLeaf from "../assets/right-list.png";

export default function SearchBar({ cities, onSearch, loading, currentCity }) {
  const [name, setName] = useState("");
  const [city, setCity] = useState(currentCity || "");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim()) {
      alert("Пожалуйста, введите название препарата");
      return;
    }
    onSearch(name.trim(), city);
  };

  return (
    <div id="search-form-div" className="search-form">
      <form id="sform" className="form-control flex" onSubmit={handleSubmit}>
        <div className="left-leaf">
          <img src={leftLeaf} alt="left leaf" />
        </div>

        <label className="form-label" htmlFor="city-select">
          Выберите город
        </label>
        <select
          name="city"
          id="city-select"
          className="form-select"
          value={city}
          onChange={(e) => setCity(e.target.value)}
        >
          <option value="">Все города</option>
          {cities.map((cityName) => (
            <option key={cityName} value={cityName}>
              {cityName}
            </option>
          ))}
        </select>

        <input
          type="text"
          id="id_q"
          name="name"
          className="form-control search-input-text"
          placeholder="Введите название, например анальгин"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />

        <button
          type="submit"
          className="search-button"
          disabled={loading}
        >
          {loading ? "Поиск..." : "Искать"}
        </button>

        <div className="right-leaf">
          <img src={rightLeaf} alt="right leaf" />
        </div>
      </form>
    </div>
  );
}
