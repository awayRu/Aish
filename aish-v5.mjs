import { complete } from "./provider-v4.mjs";
import { renderReply } from "./format-v4.mjs";
import { initExtras } from "./extras-v5.mjs";

const id = (name) => document.getElementById(name);
const prompt = id("prompt");
const scroll = id("scroll");
const output = id("messages");
const storageKey = "aish.conversations.v1";
const chats = readChats();
let chat = chats[0] ?? draft();
let job = null;
let failed = false;
let pendingDelete = null;
let view = "chat";
const drafts = new Map();
const views = { chat: id("chat-view"), library: id("library-view"), tools: id("tools-view") };

const historySearch = document.createElement("input");
historySearch.type = "search";
historySearch.id = "history-search";
historySearch.className = "history-search";
historySearch.placeholder = "Найти диалог";
historySearch.setAttribute("aria-label", "Поиск по диалогам");
id("history-list").before(historySearch);
historySearch.addEventListener("input", history);

const actions = document.createElement("div");
actions.className = "conversation-actions";
actions.id = "conversation-actions";
actions.innerHTML = '<button type="button" id="rename-chat">Переименовать</button><button type="button" id="export-chat">Скачать</button>';
document.querySelector(".model").before(actions);

const renameDialog = document.createElement("dialog");
renameDialog.innerHTML = '<form method="dialog"><h2>Название диалога</h2><label class="sr-only" for="thread-name">Название</label><input id="thread-name" maxlength="65" required><div class="dialog-actions"><button value="cancel" formnovalidate>Отмена</button><button value="save">Сохранить</button></div></form>';
document.body.append(renameDialog);

function readChats() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    return Array.isArray(saved) ? saved.filter((entry) => typeof entry?.id === "string" &&
      Array.isArray(entry.messages) && entry.messages.length &&
      entry.messages.every((message) => ["user", "assistant"].includes(message?.role) &&
        typeof message.content === "string")) : [];
  } catch {
    return [];
  }
}

function draft() {
  return { id: crypto.randomUUID(), messages: [] };
}

function title(thread) {
  if (typeof thread.name === "string" && thread.name.trim()) return thread.name.trim();
  const first = thread.messages.find(({ role }) => role === "user")?.content;
  return first ? first.replace(/\s+/g, " ").slice(0, 65) : "Новый чат";
}

function save() {
  try {
    localStorage.setItem(storageKey, JSON.stringify(chats.slice(0, 40)));
    return true;
  } catch {
    return false;
  }
}

function history() {
  const list = id("history-list");
  list.replaceChildren();
  historySearch.hidden = chats.length === 0;
  const query = historySearch.value.trim().toLocaleLowerCase("ru");
  const matching = chats.filter((entry) => !query ||
    title(entry).toLocaleLowerCase("ru").includes(query) ||
    entry.messages.some(({ content }) => content.toLocaleLowerCase("ru").includes(query)));
  if (!matching.length) {
    const empty = document.createElement("div");
    empty.className = chats.length ? "history-no-results" : "history-empty";
    empty.textContent = chats.length ? "Диалоги не найдены" : "Здесь появятся твои чаты";
    list.append(empty);
  }
  for (const thread of matching) {
    const row = document.createElement("div");
    row.className = "history-row" + (chat.id === thread.id ? " active" : "");
    const open = document.createElement("button");
    open.type = "button";
    open.className = "history-open";
    open.textContent = title(thread);
    open.title = title(thread);
    open.disabled = Boolean(job);
    if (chat.id === thread.id) open.setAttribute("aria-current", "true");
    open.onclick = () => select(thread);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "history-delete";
    remove.textContent = "×";
    remove.disabled = Boolean(job);
    remove.setAttribute("aria-label", "Удалить диалог «" + title(thread) + "»");
    remove.onclick = () => {
      pendingDelete = thread.id;
      id("remove-dialog").returnValue = "";
      id("remove-dialog").showModal();
    };
    row.append(open, remove);
    list.append(row);
  }
}

function showView(next) {
  if (!(next in views)) return;
  view = next;
  for (const [name, panel] of Object.entries(views)) panel.hidden = name !== next;
  document.querySelectorAll("[data-view]").forEach((button) => {
    if (button.dataset.view === next) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  showMenu(false);
  if (next === "chat") {
    resize();
    bottom();
  }
}

function select(thread) {
  if (job) return;
  if (chat.id !== thread.id) {
    if (chats.some((entry) => entry.id === chat.id) && prompt.value.trim()) {
      drafts.set(chat.id, prompt.value);
    } else {
      drafts.delete(chat.id);
    }
    chat = thread;
    prompt.value = drafts.get(chat.id) ?? "";
    setStatus("");
    render();
  }
  showView("chat");
  prompt.focus();
}

function usePrompt(text) {
  if (job) return false;
  showView("chat");
  prompt.value = text;
  resize();
  prompt.focus();
  return true;
}

function showMenu(open) {
  id("sidebar").classList.toggle("open", open);
  id("main").inert = open;
  id("scrim").hidden = !open;
  document.querySelectorAll("#open-menu, [data-open-menu]").forEach((button) => {
    button.setAttribute("aria-expanded", String(open));
  });
  if (open) id("close-menu").focus();
}

function resize() {
  prompt.style.height = "0";
  prompt.style.overflowY = "hidden";
  const contentHeight = prompt.scrollHeight + 2;
  const maxHeight = parseFloat(getComputedStyle(prompt).maxHeight);
  prompt.style.height = Math.min(contentHeight, maxHeight) + "px";
  if (contentHeight > maxHeight) prompt.style.overflowY = "auto";
}

function bottom() {
  scroll.scrollTop = scroll.scrollHeight;
}

function setStatus(message, retry = false) {
  id("request-status").hidden = !message;
  id("status-text").textContent = message;
  id("retry").hidden = !retry;
  failed = retry;
}

function addTurn(role, text = "") {
  const item = document.createElement("article");
  item.className = "turn " + role;
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "В" : "✳";
  const body = document.createElement("div");
  body.className = "turn-body";
  const head = document.createElement("div");
  head.className = "turn-head";
  head.textContent = role === "user" ? "Вы" : "Aish";
  const content = document.createElement("div");
  content.className = "output plain";
  body.append(head, content);
  item.append(avatar, body);
  output.append(item);

  function finish(answer) {
    if (role === "user") {
      content.textContent = answer;
      return;
    }
    content.classList.remove("plain");
    renderReply(content, answer);
    const copy = document.createElement("button");
    copy.type = "button";
    copy.className = "copy";
    copy.textContent = "Копировать";
    copy.onclick = async () => {
      try {
        await navigator.clipboard.writeText(answer);
        copy.textContent = "Скопировано";
      } catch {
        copy.textContent = "Копирование недоступно";
      }
      setTimeout(() => { copy.textContent = "Копировать"; }, 1600);
    };
    head.append(copy);
  }

  if (text) finish(text);
  return { item, content, head, finish };
}

function render() {
  history();
  actions.hidden = chat.messages.length === 0;
  id("rename-chat").disabled = Boolean(job);
  id("current-title").textContent = title(chat);
  id("welcome").hidden = chat.messages.length > 0;
  output.replaceChildren();
  for (const [index, message] of chat.messages.entries()) {
    const turn = addTurn(message.role, message.content);
    if (index === chat.messages.length - 1 && message.role === "assistant") addRegenerate(turn);
  }
  bottom();
}

function addRegenerate(turn) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy regenerate";
  button.textContent = "Ответить заново";
  button.onclick = regenerate;
  turn.head.append(button);
}

function regenerate() {
  if (job || !chat.messages.length) return;
  const previous = chat.messages.at(-1).role === "assistant" ? chat.messages.pop() : null;
  render();
  void answer(previous);
}

function exportChat() {
  const heading = title(chat).replace(/[\r\n]/g, " ");
  const text = "# " + heading + "\n\n" + chat.messages.map(({ role, content }) =>
    "## " + (role === "user" ? "Вы" : "Aish") + "\n\n" + content).join("\n\n");
  const file = new Blob([text + "\n"], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = (heading.replace(/[<>:"/\\|?*\x00-\x1f]/g, "_").replace(/[ .]+$/, "") || "Aish") + ".md";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function context() {
  // Keep recent complete turns and cap request size on long conversations.
  const recent = [];
  let budget = 20000;
  for (const message of chat.messages.slice(-13).reverse()) {
    if (message.content.length > budget) break;
    recent.unshift(message);
    budget -= message.content.length;
  }
  while (recent[0]?.role === "assistant") recent.shift();
  return [{
    role: "system",
    content: "Ты Aish, помощник для вопросов, письма и программирования. Отвечай на языке пользователя. Для сложных задач структурируй ответ и проверяй факты. Если данных не хватает, прямо скажи об этом или задай уточняющий вопрос. Не утверждай, что использовал интернет или инструменты."
  }, ...recent];
}

async function answer(previous = null) {
  const controller = new AbortController();
  let timedOut = false;
  let text = "";
  let errorMessage = "";
  job = controller;
  id("new").disabled = true;
  id("rename-chat").disabled = true;
  document.querySelectorAll(".regenerate").forEach((button) => button.remove());
  id("send").hidden = true;
  id("stop").hidden = false;
  history();
  setStatus("Запрос отправлен. Ждём модель AI Horde…");
  const turn = addTurn("assistant");
  turn.content.textContent = "Жду ответа…";
  bottom();
  const timeout = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, 100000);
  try {
    await complete(context(), controller.signal, (chunk) => {
      const following = scroll.scrollHeight - scroll.scrollTop - scroll.clientHeight < 100;
      if (!text) setStatus("Aish пишет ответ…");
      text += chunk;
      turn.content.textContent = text;
      if (following) bottom();
    });
  } catch (error) {
    if (timedOut) errorMessage = "Модель не ответила вовремя. Бесплатная очередь может быть перегружена.";
    else if (controller.signal.aborted) errorMessage = "Генерация остановлена.";
    else if (error instanceof TypeError) errorMessage = "Не удалось связаться с AI Horde. Проверь подключение и попробуй снова.";
    else errorMessage = error.message || "Не удалось получить ответ.";
  } finally {
    clearTimeout(timeout);
    job = null;
    if (text.trim()) {
      chat.messages.push({ role: "assistant", content: text.trim() });
      turn.finish(text.trim());
      addRegenerate(turn);
    } else {
      turn.item.remove();
      if (previous) {
        chat.messages.push(previous);
        addRegenerate(addTurn(previous.role, previous.content));
      }
    }
    const saved = save();
    setStatus(errorMessage || (saved ? "" : "Браузер не сохранил историю."), Boolean(errorMessage));
    id("new").disabled = false;
    id("rename-chat").disabled = false;
    id("send").hidden = false;
    id("stop").hidden = true;
    history();
  }
}

id("compose").onsubmit = (event) => {
  event.preventDefault();
  const question = prompt.value.trim();
  if (!question || job) return;
  if (!chats.some((entry) => entry.id === chat.id)) chats.unshift(chat);
  chat.messages.push({ role: "user", content: question });
  save();
  prompt.value = "";
  resize();
  render();
  void answer();
};
id("retry").onclick = () => {
  if (job || !failed || !chat.messages.length) return;
  regenerate();
};
id("stop").onclick = () => job?.abort();
id("new").onclick = () => select(draft());
document.querySelectorAll("#open-menu, [data-open-menu]").forEach((button) => {
  button.addEventListener("click", () => showMenu(true));
});
id("close-menu").onclick = id("scrim").onclick = () => {
  showMenu(false);
  views[view].querySelector("#open-menu, [data-open-menu]")?.focus();
};
id("remove-dialog").onclose = () => {
  if (id("remove-dialog").returnValue === "remove") {
    const index = chats.findIndex((entry) => entry.id === pendingDelete);
    if (index >= 0) chats.splice(index, 1);
    drafts.delete(pendingDelete);
    const saved = save();
    if (pendingDelete === chat.id) select(chats[0] ?? draft());
    else history();
    if (!saved) setStatus("Браузер не смог сохранить изменения в истории.");
  }
  pendingDelete = null;
};
matchMedia("(max-width: 47.99rem)").addEventListener("change", () => showMenu(false));
window.addEventListener("resize", () => { if (view === "chat") resize(); });
prompt.addEventListener("input", resize);
prompt.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  if (!job) id("compose").requestSubmit();
});
id("rename-chat").onclick = () => {
  id("thread-name").value = title(chat);
  renameDialog.returnValue = "";
  renameDialog.showModal();
  id("thread-name").select();
};
renameDialog.onclose = () => {
  const name = id("thread-name").value.trim();
  if (renameDialog.returnValue !== "save" || !name) return;
  chat.name = name;
  const saved = save();
  render();
  if (!saved) setStatus("Браузер не смог сохранить название.");
};
id("export-chat").onclick = exportChat;
document.querySelectorAll("[data-view]").forEach((button) => {
  button.onclick = () => {
    showView(button.dataset.view);
    if (view === "chat") prompt.focus();
    else views[view].querySelector("h1")?.focus();
  };
});
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.onclick = () => { usePrompt(button.dataset.prompt); };
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && id("sidebar").classList.contains("open") && !document.querySelector("dialog[open]")) {
    showMenu(false);
    views[view].querySelector("#open-menu, [data-open-menu]")?.focus();
  }
});
initExtras({ usePrompt });
id("main").tabIndex = -1;
for (const panel of [views.library, views.tools]) {
  const heading = panel.querySelector("h1");
  if (heading) heading.tabIndex = -1;
}
render();
showView("chat");
