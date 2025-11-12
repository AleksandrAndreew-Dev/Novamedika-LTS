import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import TelegramInit from './telegram/TelegramInit.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <TelegramInit />
    <App />
  </React.StrictMode>,
)
