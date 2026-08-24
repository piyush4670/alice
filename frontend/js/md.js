/* Tiny markdown renderer — enough for Alice's replies, safe by default. */

const ESCAPE = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function esc(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ESCAPE[ch]);
}

export function md(raw) {

  const src = esc(String(raw ?? "")).replace(/\r/g, "");

  const blocks = [];
  const fenced = src.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
    blocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
    return `\u0000${blocks.length - 1}\u0000`;
  });

  const lines = fenced.split("\n");
  const out = [];
  let list = null; // "ul" | "ol"

  const inline = (text) => text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|\W)\*([^*\n]+)\*(?=\W|$)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  const closeList = () => {
    if (list) { out.push(`</${list}>`); list = null; }
  };

  for (const line of lines) {

    const block = line.match(/^\u0000(\d+)\u0000$/);

    if (block) {
      closeList();
      out.push(blocks[Number(block[1])]);
      continue;
    }

    if (!line.trim()) { closeList(); continue; }

    const header = line.match(/^(#{1,3})\s+(.*)$/);

    if (header) {
      closeList();
      out.push(`<h3>${inline(header[2])}</h3>`);
      continue;
    }

    if (/^(---|\*\*\*|___)$/.test(line.trim())) {
      closeList();
      out.push("<hr>");
      continue;
    }

    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);

    if (bullet) {
      if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; }
      out.push(`<li>${inline(bullet[1])}</li>`);
      continue;
    }

    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);

    if (numbered) {
      if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; }
      out.push(`<li>${inline(numbered[1])}</li>`);
      continue;
    }

    closeList();
    out.push(`<p>${inline(line)}</p>`);
  }

  closeList();

  return out.join("");
}

/* Strip markdown for speech. */
export function plain(raw) {

  return String(raw ?? "")
    .replace(/```[\s\S]*?```/g, " code block ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^[-*•]\s*/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}
