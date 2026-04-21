import React from "react";

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-telegram-bg">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-telegram-border">
        <div className="max-w-4xl mx-auto py-4 px-4 flex items-center">
          <a
            href="/"
            className="flex items-center text-telegram-primary hover:text-blue-700 transition-colors mr-4"
          >
            <svg
              className="w-5 h-5 mr-1"
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
            На главную
          </a>
          <h1 className="text-xl font-bold text-telegram-primary">
            Политика конфиденциальности
          </h1>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6 text-gray-800">
          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              1. Общие положения
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>
                Настоящая Политика определяет порядок обработки персональных
                данных в информационной системе <strong>NovaMedika2</strong> —
                справочном сервисе поиска лекарственных средств, оформления
                заказов и проведения онлайн-консультаций между пользователями и
                фармацевтами (далее — Сервис).
              </p>
              <p>
                Оператор: <strong>[НАИМЕНОВАНИЕ ОРГАНИЗАЦИИ]</strong>. Сервис
                доступен по адресам: spravka.novamedika.com,
                api.spravka.novamedika.com, Telegram-бот @Novamedika_bot.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              2. Какие данные мы собираем
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>Мы обрабатываем следующие персональные данные:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>
                  <strong>Пользователи:</strong> Telegram ID, имя, фамилия,
                  номер телефона (при предоставлении), текст вопроса
                </li>
                <li>
                  <strong>Фармацевты:</strong> Telegram ID, имя, фамилия,
                  отчество, номер телефона, статус, данные о квалификации
                </li>
                <li>
                  <strong>Заказчики:</strong> имя, номер телефона, наименование
                  продукта, аптека, количество
                </li>
                <li>
                  <strong>Технические данные:</strong> IP-адреса, логи
                  аутентификации, данные сессий
                </li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              3. Цели обработки данных
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Регистрация и обслуживание фармацевтов</li>
                <li>Проведение онлайн-консультаций (Q&A система)</li>
                <li>Оформление заказов на лекарства</li>
                <li>Синхронизация данных с аптеками-партнёрами</li>
                <li>Обеспечение информационной безопасности</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              4. Правовые основания
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>
                Обработка осуществляется на основании:
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Согласия субъекта персональных данных</li>
                <li>Исполнения договора</li>
                <li>Требований законодательства Республики Беларусь</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              5. Сроки хранения
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border border-gray-200 rounded-lg">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-3 font-semibold border-b">
                      Категория
                    </th>
                    <th className="text-left p-3 font-semibold border-b">
                      Срок
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="p-3">Данные пользователей (Q&A)</td>
                    <td className="p-3">1 год после последнего обращения</td>
                  </tr>
                  <tr className="border-b">
                    <td className="p-3">Данные фармацевтов</td>
                    <td className="p-3">
                      1 год после прекращения сотрудничества
                    </td>
                  </tr>
                  <tr className="border-b">
                    <td className="p-3">Заказы на лекарства</td>
                    <td className="p-3">3 года с даты оформления</td>
                  </tr>
                  <tr className="border-b">
                    <td className="p-3">Логи (события ИБ)</td>
                    <td className="p-3">1 год с даты создания</td>
                  </tr>
                  <tr>
                    <td className="p-3">CSV-данные аптек</td>
                    <td className="p-3">
                      До следующей синхронизации + 30 дней
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              6. Ваши права
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>Вы имеете право:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Получить доступ к своим персональным данным</li>
                <li>Изменить или уточнить свои данные</li>
                <li>Требовать удаления данных</li>
                <li>Отозвать согласие на обработку</li>
                <li>Получить копию данных в машиночитаемом формате</li>
                <li>
                  Обжаловать действия Оператора в Национальный центр защиты
                  персональных данных
                </li>
              </ul>
              <p className="mt-3">
                Для реализации прав напишите на email:{" "}
                <a
                  href="mailto:privacy@novamedika.com"
                  className="text-telegram-primary hover:underline"
                >
                  privacy@novamedika.com
                </a>
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              7. Защита данных
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>
                Мы применяем следующие меры защиты:
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Шифрование передаваемых данных (HTTPS/TLS)</li>
                <li>JWT-аутентификация с ограниченным сроком действия</li>
                <li>Разграничение доступа по ролям</li>
                <li>Изоляция контейнеров Docker</li>
                <li>Резервное копирование данных</li>
                <li>Мониторинг событий информационной безопасности</li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              8. Внешние сервисы и ссылки
            </h2>
            <div className="space-y-2 text-sm leading-relaxed">
              <p>
                Сервис содержит ссылки на внешние ресурсы, которые открываются по инициативе пользователя:
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>
                  <strong>Картографические сервисы</strong> (Google Maps, Yandex Maps, OpenStreetMap) — для отображения расположения аптек
                </li>
              </ul>
              <p className="mt-2">
                При переходе на внешние ресурсы:
              </p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Переход осуществляется по явной инициативе пользователя (клик по ссылке)</li>
                <li>Ссылки открываются в новой вкладке браузера с атрибутами безопасности</li>
                <li>Передаются только публичные данные (адреса аптек)</li>
                <li><strong>Персональные данные пользователей НЕ передаются</strong> внешним сервисам</li>
              </ul>
              <p className="mt-2 text-gray-600">
                Оператор не контролирует политику конфиденциальности внешних сервисов. Пользователям рекомендуется ознакомиться с их политиками перед использованием.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              9. Трансграничная передача
            </h2>
            <div className="text-sm leading-relaxed">
              <p>
                Оператор <strong>не осуществляет</strong> трансграничную
                передачу персональных данных. Обработка данных осуществляется на
                территории Республики Беларусь.
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              10. Контактные данные
            </h2>
            <div className="text-sm leading-relaxed">
              <p>
                Лицо, ответственное за защиту персональных данных:
              </p>
              <div className="mt-2 bg-gray-50 rounded-lg p-4">
                <p>
                  <strong>Email:</strong>{" "}
                  <a
                    href="mailto:privacy@novamedika.com"
                    className="text-telegram-primary hover:underline"
                  >
                    privacy@novamedika.com
                  </a>
                </p>
                <p>
                  <strong>Телефон:</strong> [ТЕЛЕФОН]
                </p>
              </div>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-bold text-telegram-primary mb-3">
              11. Изменения в Политике
            </h2>
            <div className="text-sm leading-relaxed">
              <p>
                Оператор вправе вносить изменения в настоящую Политику. При
                существенных изменениях мы уведомим вас заблаговременно. Новая
                версия публикуется на этой странице.
              </p>
            </div>
          </section>

          <div className="pt-4 border-t text-sm text-gray-500">
            <p>
              Версия: 1.1 | Дата обновления: 21 апреля 2026 г.
            </p>
            <p className="mt-1">
              Документ составлен в соответствии с Законом Республики Беларусь
              №99-З «О защите персональных данных» от 07.05.2021.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
