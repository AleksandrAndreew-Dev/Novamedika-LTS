import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import TelegramInit from "./telegram/TelegramInit.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import "./index.css";

// Smooth loading: show body with fade-in, then hide spinner
document.body.classList.add("loaded");

const loadingElement = document.getElementById("loading");
if (loadingElement) {
  // Hide spinner after body fade-in
  setTimeout(() => {
    loadingElement.classList.add("hidden");
    // Remove from DOM after transition completes
    setTimeout(() => {
      loadingElement.remove();
    }, 300);
  }, 100);
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <TelegramInit />
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
