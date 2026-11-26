const categories = ["Учёба", "Текст", "Код", "Планирование"];
const templates = [
  ["Учёба", "Объяснение с примером", "Разберись в незнакомой теме шаг за шагом.",
    "Объясни [тему] простыми словами. Начни с примера из жизни, затем объясни, как он связан с темой. В конце задай два вопроса, чтобы я мог проверить себя."],
  ["Учёба", "Карточки для повторения", "Преврати конспект в вопросы и короткие ответы.",
    "Сделай из моего конспекта 8 карточек для повторения. Для каждой дай вопрос и короткий ответ. Отдельно отметь понятия, которые легко перепутать.\n\nКонспект:\n[вставь текст]"],
  ["Учёба", "Мини-тест", "Потренируйся и получи разбор ошибок.",
    "Проведи мини-тест по теме [тема]. Задавай по одному вопросу и жди моего ответа. Если я ошибусь, объясни решение и дай похожее задание."],
  ["Учёба", "Сравнение понятий", "Увидь разницу на конкретных примерах.",
    "Сравни [понятие 1] и [понятие 2]. Покажи, что у них общего, где они различаются и когда полезно каждое из них. Добавь по одному примеру."],
  ["Текст", "Письмо или сообщение", "Подбери формулировки для адресата и ситуации.",
    "Помоги написать сообщение [кому] о том, что [ситуация]. Цель сообщения — [цель]. Сделай два коротких варианта: нейтральный и дружелюбный."],
  ["Текст", "Редактура черновика", "Убери повторы и сделай мысль яснее.",
    "Улучши этот текст. Сохрани мой тон, факты и смысл. Сократи повторы и замени неясные формулировки. Если предложение двусмысленно, отметь его отдельно.\n\n[вставь текст]"],
  ["Текст", "Перевод с нюансами", "Сохрани смысл, тон и формат оригинала.",
    "Переведи текст на [язык]. Сохрани тон и формат. Для идиом подбери естественный аналог. Отдельно поясни выбор формулировок, только если есть неоднозначность.\n\n[вставь текст]"],
  ["Текст", "Резюме документа", "Выдели смысл, выводы и открытые вопросы.",
    "Сделай резюме по тексту ниже. Начни с главного вывода, затем перечисли 3–5 опорных фактов. Если текст содержит решения или вопросы без ответа, вынеси их отдельно.\n\n[вставь текст]"],
  ["Код", "Разбор кода", "Пойми, что делает фрагмент и где его границы.",
    "Разбери этот код для человека, который только знакомится с [язык]. Объясни назначение частей и покажи пример входных данных и результата. Укажи граничные случаи, которые стоит проверить.\n\n[вставь код]"],
  ["Код", "Поиск причины ошибки", "Проверь стек вызовов и предложи точечное исправление.",
    "Помоги найти причину ошибки. Сначала объясни, какую строку стоит проверить и почему. Предложи минимальную правку и способ убедиться, что она работает.\n\nЧто ожидал: [результат]\nТекст ошибки: [ошибка]\nКод: [фрагмент]"],
  ["Код", "Ревью и проверка", "Найди логические баги и важные граничные случаи.",
    "Проведи ревью фрагмента. Сначала перечисли конкретные логические ошибки и сценарии, в которых они проявятся. Предложи небольшие исправления и примеры входных данных для проверки.\n\n[вставь код]"],
  ["Код", "Выбор подхода", "Сравни варианты для задачи перед реализацией.",
    "Помоги выбрать подход для [задача]. Условия: [язык, объём данных, ограничения]. Сравни 2–3 варианта по простоте, скорости и поддержке. Приведи маленький пример для рекомендованного варианта."],
  ["Планирование", "План на неделю", "Разбей цель на дни с измеримым результатом.",
    "Составь реалистичный план на неделю для цели [цель]. В день у меня есть [время]. Для каждого дня укажи задачу и способ проверить результат. Оставь время на повторение и перенос задач."],
  ["Планирование", "Старт проекта", "Определи первый результат, шаги и зависимости.",
    "Помоги начать проект [идея]. Выдели первый полезный результат, который можно сделать за [срок]. Разбей его на шаги, укажи зависимости и вопросы, которые нужно решить."],
  ["Планирование", "Сравнение вариантов", "Прими решение по нескольким критериям.",
    "Помоги сравнить варианты [варианты]. Мои приоритеты: [критерии]. Объясни компромиссы, обозначь недостающие данные и предложи простой способ проверить лучший вариант."],
  ["Планирование", "План встречи", "Подготовь повестку с решениями и сроками.",
    "Составь повестку встречи на [длительность] по теме [тема]. Укажи, что участникам подготовить, какие решения нужно принять и как зафиксировать следующие шаги."]
];

const toneNames = ["Нейтральный", "Дружелюбный", "Деловой", "Максимально простой"];
const favoritesKey = "aish.prompt-favorites.v1";
const wordSegments = typeof Intl.Segmenter === "function"
  ? new Intl.Segmenter("ru", { granularity: "word" })
  : null;

function create(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function button(label, className = "extras-button") {
  const node = create("button", className, label);
  node.type = "button";
  return node;
}

function heading(title, description) {
  const node = create("header", "extras-heading");
  const titleNode = create("h1", "", title);
  titleNode.tabIndex = -1;
  node.append(titleNode, create("p", "", description));
  return node;
}

function labelText(text, field) {
  const label = create("label", "extras-label");
  label.append(create("span", "", text), field);
  return label;
}

function useDraft(usePrompt, text, status) {
  status.textContent = usePrompt(text) === false ? "Сначала заверши текущий ответ в чате." : "";
}

function initLibrary(mount, usePrompt) {
  const favorites = new Set();
  try {
    const saved = JSON.parse(localStorage.getItem(favoritesKey));
    if (Array.isArray(saved)) {
      for (const index of saved) if (Number.isInteger(index) && templates[index]) favorites.add(index);
    }
  } catch {
    // Favorites remain usable during the current session.
  }

  const search = create("input", "extras-field");
  search.type = "search";
  search.placeholder = "Название, тема или задача";
  search.maxLength = 120;
  const filters = create("div", "extras-filters");
  filters.setAttribute("role", "group");
  filters.setAttribute("aria-label", "Категории шаблонов");
  const status = create("p", "extras-status");
  status.setAttribute("role", "status");
  const grid = create("div", "extras-library-grid");
  const filterButtons = new Map();
  let selected = "Все";

  function render() {
    const query = search.value.trim().toLocaleLowerCase("ru");
    const entries = templates.map((entry, index) => ({ entry, index })).filter(({ entry, index }) => {
      return (selected === "Все" || entry[0] === selected || (selected === "Избранное" && favorites.has(index)))
        && entry.join(" ").toLocaleLowerCase("ru").includes(query);
    });
    for (const [name, element] of filterButtons) {
      element.setAttribute("aria-pressed", String(selected === name));
    }
    grid.replaceChildren();
    if (!entries.length) {
      grid.append(create("p", "extras-empty", selected === "Избранное" && !favorites.size
        ? "Нажми на звёздочку у шаблона, чтобы сохранить его здесь."
        : "Подходящие шаблоны не найдены. Попробуй другой запрос или раздел."));
    }
    for (const { entry: [category, title, description, prompt], index } of entries) {
      const card = create("article", "extras-card extras-template");
      const top = create("div", "extras-template-head");
      const star = button(favorites.has(index) ? "★" : "☆", "extras-favorite");
      star.setAttribute("aria-label", "Избранное для шаблона «" + title + "»");
      star.setAttribute("aria-pressed", String(favorites.has(index)));
      star.onclick = () => {
        if (favorites.has(index)) favorites.delete(index);
        else favorites.add(index);
        try {
          localStorage.setItem(favoritesKey, JSON.stringify([...favorites]));
          status.textContent = "";
        } catch {
          status.textContent = "Браузер не сохранил избранное за пределами этой вкладки.";
        }
        if (selected === "Избранное") {
          render();
          filterButtons.get("Избранное").focus();
        } else {
          star.textContent = favorites.has(index) ? "★" : "☆";
          star.setAttribute("aria-pressed", String(favorites.has(index)));
        }
      };
      top.append(create("span", "extras-category", category), star);
      const open = button("Открыть в чате", "extras-button extras-template-open");
      open.setAttribute("aria-label", "Открыть в чате шаблон «" + title + "»");
      open.onclick = () => useDraft(usePrompt, prompt, status);
      card.append(top, create("h2", "", title), create("p", "", description), open);
      grid.append(card);
    }
  }

  for (const name of ["Все", ...categories, "Избранное"]) {
    const filter = button(name, "extras-filter");
    filter.onclick = () => {
      selected = name;
      status.textContent = "";
      render();
    };
    filterButtons.set(name, filter);
    filters.append(filter);
  }
  search.addEventListener("input", () => {
    status.textContent = "";
    render();
  });
  mount.replaceChildren(
    heading("Библиотека шаблонов", "Выбери запрос и дополни его перед отправкой в чат."),
    labelText("Поиск по шаблонам", search), filters, status, grid
  );
  render();
}

function cleanText(text) {
  return text.trim().split(/\r?\n/).map((line) => line.trim().replace(/[^\S\r\n]+/g, " "))
    .join("\n").replace(/\n{3,}/g, "\n\n");
}

function removeDuplicateLines(text) {
  const seen = new Set();
  return text.split(/\r?\n/).filter((line) => {
    const normalized = line.trim();
    if (!normalized) return true;
    if (seen.has(normalized)) return false;
    seen.add(normalized);
    return true;
  }).join("\n");
}

function wordCount(text) {
  if (!wordSegments) return (text.match(/[\p{L}\p{N}]+/gu) ?? []).length;
  let count = 0;
  for (const part of wordSegments.segment(text)) if (part.isWordLike) count++;
  return count;
}

function initEditor(usePrompt) {
  const editor = create("section", "extras-card extras-workspace");
  const display = create("div", "extras-metrics");
  const metrics = ["Слова", "Символы", "Строки", "Время чтения"].map((name) => {
    const field = create("div", "extras-metric");
    const value = create("strong", "", "0");
    field.append(value, create("span", "", name));
    display.append(field);
    return value;
  });
  const source = create("textarea", "extras-field extras-area");
  source.rows = 7;
  source.maxLength = 6500;
  source.placeholder = "Вставь сюда заметки, черновик, письмо или список";
  const localActions = create("div", "extras-actions");
  const aiActions = create("div", "extras-actions");
  const status = create("p", "extras-status");
  status.setAttribute("role", "status");
  let previous = null;
  const undo = button("Отменить");
  const copy = button("Копировать");
  const reset = button("Очистить");

  const transformations = [
    ["Убрать лишние пробелы", cleanText],
    ["Удалить повторные строки", removeDuplicateLines],
    ["ВЕРХНИЙ регистр", (value) => value.toLocaleUpperCase("ru")],
    ["нижний регистр", (value) => value.toLocaleLowerCase("ru")]
  ].map(([label, transform]) => {
    const item = button(label);
    item.onclick = () => apply(transform(source.value), "Текст обновлён.");
    localActions.append(item);
    return item;
  });

  const aiButtons = [
    ["Сократить", "Сократи этот текст, сохрани главную мысль, факты и тон."],
    ["Проверить стиль", "Предложи редактуру текста. Исправь ошибки и неудачные формулировки, сохрани тон и смысл."],
    ["Выделить задачи", "Извлеки из текста задачи. Если указаны ответственные или сроки, добавь их к каждому пункту."],
    ["Объяснить проще", "Перепиши текст простыми словами. Сохрани факты и добавь короткое пояснение сложных терминов."]
  ].map(([label, instruction]) => {
    const item = button(label, "extras-button extras-accent");
    item.onclick = () => useDraft(usePrompt, instruction + "\n\nТекст:\n" + source.value.trim(), status);
    aiActions.append(item);
    return item;
  });

  function update() {
    const text = source.value;
    const words = wordCount(text);
    const values = [words, [...text].length, text ? text.split(/\r?\n/).length : 0,
      words ? Math.max(1, Math.ceil(words / 200)) + " мин" : "0 мин"];
    metrics.forEach((metric, index) => { metric.textContent = String(values[index]); });
    for (const item of [...transformations, ...aiButtons]) item.disabled = !text.trim();
    copy.disabled = !text;
    reset.disabled = !text;
    undo.disabled = previous === null;
  }

  function apply(value, feedback) {
    if (value === source.value) {
      status.textContent = "Текст уже подходит.";
      return;
    }
    if (value.length > source.maxLength) {
      status.textContent = "После обработки текст превысит допустимые 6500 символов.";
      return;
    }
    previous = source.value;
    source.value = value;
    status.textContent = feedback;
    update();
  }

  undo.onclick = () => {
    if (previous === null) return;
    source.value = previous;
    previous = null;
    status.textContent = "Последнее изменение отменено.";
    update();
  };
  copy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(source.value);
      status.textContent = "Текст скопирован.";
    } catch {
      source.select();
      status.textContent = "Текст выделен. Скопируй его через меню браузера.";
    }
  };
  reset.onclick = () => apply("", "Поле очищено. Действие можно отменить.");
  source.addEventListener("input", () => {
    previous = null;
    status.textContent = "";
    update();
  });

  localActions.append(copy, undo, reset);
  editor.append(
    create("h2", "", "Редактор текста"), display, labelText("Текст для работы (до 6500 символов)", source),
    create("h3", "", "Быстрые действия"), localActions,
    create("h3", "", "Действия с ИИ"), aiActions, status
  );
  update();
  return editor;
}

function initBuilder(usePrompt) {
  const builder = create("form", "extras-card extras-workspace");
  const goal = create("input", "extras-field");
  goal.placeholder = "Например, подготовить план урока";
  goal.maxLength = 240;
  goal.required = true;
  const details = create("textarea", "extras-field extras-area");
  details.rows = 3;
  details.maxLength = 1000;
  details.placeholder = "Аудитория, материал, примеры";
  const result = create("input", "extras-field");
  result.placeholder = "Например, таблица на 5 строк";
  result.maxLength = 200;
  const tone = create("select", "extras-field");
  for (const name of toneNames) tone.append(create("option", "", name));
  const status = create("p", "extras-status");
  status.setAttribute("role", "status");
  const send = create("button", "extras-button extras-primary", "Собрать и открыть в чате");
  send.type = "submit";
  builder.append(
    create("h2", "", "Конструктор запроса"),
    create("p", "", "Укажи задачу и нужный формат, чтобы получить более точный ответ."),
    labelText("Что нужно сделать", goal), labelText("Контекст", details),
    labelText("Формат ответа", result), labelText("Тон ответа", tone), send, status
  );
  builder.onsubmit = (event) => {
    event.preventDefault();
    if (!goal.value.trim()) {
      status.textContent = "Укажи, что нужно сделать.";
      goal.focus();
      return;
    }
    const parts = ["Задача — " + goal.value.trim()];
    if (details.value.trim()) parts.push("Контекст — " + details.value.trim());
    if (result.value.trim()) parts.push("Формат ответа — " + result.value.trim());
    parts.push("Тон ответа — " + tone.value.toLocaleLowerCase("ru"));
    useDraft(usePrompt, parts.join("\n\n"), status);
  };
  return builder;
}

export function initExtras({ usePrompt }) {
  const library = document.getElementById("library-content");
  const tools = document.getElementById("tools-content");
  initLibrary(library, usePrompt);
  const workspaces = create("div", "extras-workspaces");
  workspaces.append(initEditor(usePrompt), initBuilder(usePrompt));
  tools.replaceChildren(
    heading("Инструменты", "Обработай текст в браузере или собери запрос для Aish."),
    workspaces
  );
}
