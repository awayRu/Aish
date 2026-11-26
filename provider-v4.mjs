export const MODEL = "Qwen/Qwen3.8-Flash-Next";
const ENDPOINT = "https://oai.aihorde.net/v1/chat/completions";

export async function complete(messages, signal, onText) {
  const response = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: "Bearer 0000000000", "Content-Type": "application/json" },
    body: JSON.stringify({
      model: MODEL, messages, stream: true, max_tokens: 1500, temperature: 0.6
    }),
    signal
  });
  if (!response.ok) {
    if ([429, 503, 504].includes(response.status)) {
      throw new Error("Бесплатная очередь AI Horde перегружена. Попробуй повторить запрос чуть позже.");
    }
    throw new Error("AI Horde не смог выполнить запрос (HTTP " + response.status + ").");
  }
  if (response.headers.get("content-type")?.includes("application/json")) {
    const packet = await response.json();
    const content = packet.choices?.[0]?.message?.content;
    if (typeof content !== "string" || !content.trim()) throw emptyReply();
    onText(content);
    return;
  }
  if (!response.body) throw emptyReply();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let complete = false;
  let answered = false;
  try {
    while (!complete) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split(/\r?\n/);
      buffer = done ? "" : lines.pop();
      if (buffer.length > 262144) throw new Error("AI Horde вернул слишком большой фрагмент ответа.");
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (raw === "[DONE]") {
          complete = true;
          break;
        }
        if (!raw) continue;
        const packet = JSON.parse(raw);
        if (packet.error) throw new Error("AI Horde прервал генерацию. Пробуй снова чуть позже.");
        const choice = packet.choices?.[0];
        const fragment = choice?.delta?.content;
        if (typeof fragment === "string" && fragment) {
          onText(fragment);
          answered ||= Boolean(fragment.trim());
        }
        if (choice?.finish_reason) complete = true;
      }
      if (done) break;
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
  if (!answered) throw emptyReply();
  if (!complete) throw new Error("Соединение прервалось до конца ответа.");
}

function emptyReply() {
  return new Error("Модель не прислала текст. Попробуй отправить вопрос снова.");
}
