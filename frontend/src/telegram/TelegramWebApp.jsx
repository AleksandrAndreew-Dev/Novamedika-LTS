/* eslint-disable react-refresh/only-export-components */
// Реэкспорт из TelegramContext для обратной совместимости
// Все хуки теперь используют единый Context
export {
  TelegramProvider,
  useTelegramContext,
  useTelegramWebApp,
  useTelegramUser,
  useTelegramAPI,
} from "./TelegramContext";
