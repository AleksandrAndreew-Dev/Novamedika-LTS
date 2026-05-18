Ок — тогда приоритет: **1) стабильность Telegram BackButton**, **2) меньше лишних перерисовок/DOM**, **3) меньше “тяжёлых” вычислений при каждом рендере**. Ниже — короткий чек‑лист с максимально “безопасными” правками (поведение не меняем).

## A. Стабильность: Telegram BackButton (обязательно)

### 1) Подписка/отписка на один и тот же handler

Сейчас есть риск, что обработчики накапливаются (и Back жмётся “ступенями”).

Замените ваш useEffect на вариант с **стабильной функцией**:

```jsx
const onTgBack = useCallback(() => {
  setStep((s) => Math.max(1, s - 1));
}, []);

useEffect(() => {
  if (!isTelegram || !tg) return;

  if (step === 1) tg.BackButton.hide();
  else tg.BackButton.show();

  tg.BackButton.onClick(onTgBack);
  return () => tg.BackButton.offClick(onTgBack);
}, [step, isTelegram, tg, onTgBack]);
```

Почему это важно:

- `offClick()` без аргумента (или с другой функцией) часто **не снимает** предыдущий обработчик.
- Это напрямую влияет на стабильность (особенно в Telegram WebView).

### 2) Не трогать BackButton, когда `tg` ещё не готов

Вы это уже делаете (`if (!isTelegram || !tg) return;`) — оставить так.

---

## B. Скорость/перерисовки: убрать лишний рендер и лишний DOM

### 3) Убрать дубль пагинации в SearchResults.jsx

У вас пагинация рендерится дважды: один раз внутри блока результатов, и второй раз внизу (и ещё там используется `total_pages`, которого нет в вашем state — значит это либо мёртвый код, либо потенциальная ошибка).

Безопасно: **удалить нижний блок**:

```jsx
{
  /* Pagination */
}
{
  pagination && pagination.total_pages > 1 && !loading && (
    <SearchResultsPagination
      pagination={pagination}
      onPageChange={onPageChange}
    />
  );
}
```

Результат:

- меньше DOM,
- меньше ререндеров пагинации,
- убираете путаницу `totalPages` vs `total_pages`.

### 4) Не используйте `index` как key для списка результатов

Сейчас:

```jsx
{groupedResults.map((item, index) => (
  <ResultItemTelegram key={index} ... />
))}
```

Лучше (стабильный ключ):

```jsx
const key = `${item.pharmacy_id}|${item.product_uuid}|${item.name}|${item.form}|${item.manufacturer ?? ""}`;

<ResultItemTelegram key={key} ... />
```

Это уменьшает “мигание” и лишние размонтирования/монтирования карточек при:

- переключении страниц,
- изменении фильтров,
- обновлении данных.

---

## C. Скорость: группировка результатов (самое тяжёлое место)

### 5) Упростить вычисления в groupedResults: меньше Date/new и массивов

Вы сейчас храните `quantities: []`, `prices: []`, потом `reduce`, `Math.min`. Это ок, но можно сделать дешевле без изменения результата: хранить сразу агрегаты.

Идея:

- `sumQuantity`
- `minPrice`
- `pricesSetCount` или флаг `hasMultiplePrices`

Пример (концептуально, без ломки логики):

```jsx
if (!grouped[key]) {
  grouped[key] = {
    ...item,
    quantitySum: q,
    minPrice: price,
    priceSeen: new Set([price]),
    ...
  };
} else {
  grouped[key].quantitySum += q;
  grouped[key].minPrice = Math.min(grouped[key].minPrice, price);
  grouped[key].priceSeen.add(price);
}
```

На выходе:

```jsx
quantity: item.quantitySum,
price: item.minPrice,
hasMultiplePrices: item.priceSeen.size > 1,
```

Это сокращает:

- создание массивов,
- reduce/min по массивам,
- количество аллокаций.

### 6) Date.parse вместо new Date в цикле

Внутри циклов `new Date(...)` дороговат. Безопаснее:

```jsx
const ts = Date.parse(item.updated_at || "") || 0;
```

---

## D. Дополнительно для стабильности сети/отмены запросов (не ломая UX)

### 7) Корректно обрабатывать отмену запросов (axios + AbortController)

Сейчас вы ловите только `"CanceledError"`. Лучше:

```jsx
const isCanceled =
  error?.name === "CanceledError" ||
  error?.name === "AbortError" ||
  error?.code === "ERR_CANCELED";

if (isCanceled) return;
```

Это уберёт ложные “Ошибка при поиске” при быстрой смене шагов/параметров.

---

## Приоритет внедрения (в вашем порядке важности)

1. **BackButton handler + offClick(handler)** (A1)

2. **Убрать дубль пагинации** (B3)

3. **Стабильные key вместо index** (B4)

4. **Оптимизировать groupedResults (агрегаты + Date.parse)** (C5–C6)

5. **Улучшить cancel‑детект** (D7)

Если хотите, скиньте, пожалуйста, ваш файл `TelegramContext` / `useTelegramWebApp` (или кусок, где создаётся `tg`), и я скажу, есть ли там ещё типичные источники “глюков BackButton” (например, повторная инициализация объекта или слушателей).
