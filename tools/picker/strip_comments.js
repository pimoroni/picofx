const fs = require("fs");
const acorn = require("acorn");

for (const file of process.argv.slice(2)) {
  const text = fs.readFileSync(file, "utf8");
  const comments = [];
  acorn.parse(text, {ecmaVersion: 2022, sourceType: "module", onComment: comments});
  let out = text;
  for (const comment of comments.reverse()) {
    let start = comment.start;
    let end = comment.end;
    const lineStart = out.lastIndexOf("\n", start - 1) + 1;
    const lineEnd = out.indexOf("\n", end);
    const before = out.slice(lineStart, start);
    const after = out.slice(end, lineEnd === -1 ? out.length : lineEnd);
    if (!before.trim() && !after.trim()) {
      start = lineStart;
      end = lineEnd === -1 ? out.length : lineEnd + 1;
    } else if (!after.trim()) {
      start = lineStart + before.trimEnd().length;
    }
    out = out.slice(0, start) + out.slice(end);
  }
  out = out.replace(/\n{3,}/g, "\n\n").replace(/^\n+/, "").replace(/\{\n\n/g, "{\n");
  if (out !== text) fs.writeFileSync(file, out);
}
