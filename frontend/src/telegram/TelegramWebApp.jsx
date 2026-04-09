// Реэкспорт из TelegramContext для обратной совместимости
// Все хуки теперь используют единый Context
export {
  TelegramProvider,
  useTelegramContext,
  useTelegramWebApp,
  useTelegramUser,
  useTelegramAPI,
} from "./TelegramContext";
