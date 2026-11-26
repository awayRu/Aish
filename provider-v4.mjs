export const MODEL = "gemma-4-26b-a4b";
const providers = [
  {
    endpoint: "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions",
    model: MODEL,
    headers: { "Content-Type": "application/json" }
  },
  {
    endpoint: "https://oai.aihorde.net/v1/chat/completions",
    model: "koboldcpp/Qwen3-14B",
    headers: { Authorization: "Bearer 0000000000", "Content-Type": "application/json" }
  }
];

export async function complete(messages, signal, onText) {
  let error;
  for (const provider of providers) {
    let started = false;
    try {
      await streamReply(provider, messages, signal, (fragment) => {
        started = true;
        onText(fragment);
      });
      return;
    } catch (failure) {
      if (signal?.aborted || started) throw failure;
      error = failure;
    }
  }
  throw error;
}

async function streamReply(provider, messages, signal, onText) {
  const response = await fetch(provider.endpoint, {
    method: "POST",
    headers: provider.headers,
    body: JSON.stringify({
      model: provider.model, messages, stream: true, max_tokens: 1500, temperature: 0.6
    }),
    signal
  });
  if (!response.ok) {
    if ([429, 503, 504].includes(response.status)) {
      throw new Error("Бесплатные модели сейчас перегружены. Попробуй повторить запрос чуть позже.");
    }
    throw new Error("Модель не смогла выполнить запрос (HTTP " + response.status + ").");
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
      if (buffer.length > 262144) throw new Error("Модель вернула слишком большой фрагмент ответа.");
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (raw === "[DONE]") {
          complete = true;
          break;
        }
        if (!raw) continue;
        const packet = JSON.parse(raw);
        if (packet.error) throw new Error("Модель прервала генерацию. Пробуй снова чуть позже.");
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
