const inline = (node, line) => {
  const parts = line.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g);
  for (const part of parts) {
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      const code = document.createElement("code");
      code.textContent = part.slice(1, -1);
      node.append(code);
    } else if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      const bold = document.createElement("strong");
      bold.textContent = part.slice(2, -2);
      node.append(bold);
    } else {
      node.append(document.createTextNode(part));
    }
  }
};

export function renderReply(target, text) {
  target.replaceChildren();
  const lines = text.split(/\r?\n/);
  for (let index = 0; index < lines.length;) {
    const line = lines[index++];
    if (!line.trim()) continue;
    if (/^\s*```/.test(line)) {
      const body = [];
      while (index < lines.length && !/^\s*```/.test(lines[index])) body.push(lines[index++]);
      if (index < lines.length) index++;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      code.textContent = body.join("\n");
      pre.append(code);
      target.append(pre);
      continue;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const block = document.createElement("h" + Math.min(heading[1].length + 1, 4));
      inline(block, heading[2]);
      target.append(block);
      continue;
    }
    const unordered = /^\s*[-*+]\s+(.*)$/;
    const ordered = /^\s*\d+\.\s+(.*)$/;
    const pattern = unordered.test(line) ? unordered : ordered.test(line) ? ordered : null;
    if (pattern) {
      const list = document.createElement(pattern === ordered ? "ol" : "ul");
      let match = pattern.exec(line);
      while (match) {
        const item = document.createElement("li");
        inline(item, match[1]);
        list.append(item);
        match = pattern.exec(lines[index] ?? "");
        if (match) index++;
      }
      target.append(list);
      continue;
    }
    const paragraph = document.createElement("p");
    inline(paragraph, line);
    target.append(paragraph);
  }
}
