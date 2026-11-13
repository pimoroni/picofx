const fs = require("fs");
const acorn = require("acorn");

const [file, ...names] = process.argv.slice(2);
const text = fs.readFileSync(file, "utf8");
const ast = acorn.parse(text, {ecmaVersion: 2022, sourceType: "module", ranges: true});
const wanted = new Set(names.filter(name => !name.startsWith("call:")));
const calls = names.filter(name => name.startsWith("call:")).map(name => name.slice(5));

function declared(node) {
  const inner = node.type === "ExportNamedDeclaration" ? node.declaration : node;
  if (!inner) return [];
  if (inner.id) return [inner.id.name];
  return (inner.declarations || []).map(one => one.id.name);
}

function calling(node) {
  const source = text.slice(node.start, node.end);
  return calls.find(call => source.startsWith(call)) || null;
}

const cuts = [];
const found = new Set();
for (const node of ast.body) {
  const names = declared(node);
  const hit = names.length && names.every(name => wanted.has(name));
  const call = calling(node);
  if (!hit && !call) continue;
  names.forEach(name => found.add(name));
  if (call) found.add("call:" + call);
  let start = node.start;
  while (true) {
    const lineStart = text.lastIndexOf("\n", start - 2) + 1;
    if (!text.slice(lineStart, start).trim().startsWith("//")) break;
    start = lineStart;
  }
  let end = node.end;
  while (text[end] === "\n") end++;
  cuts.push([start, end]);
}
const missing = names.filter(name => !found.has(name));
if (missing.length) {
  console.error(file + ": not found: " + missing.join(", "));
  process.exit(1);
}
let out = text;
cuts.sort((a, b) => b[0] - a[0]).forEach(([start, end]) => { out = out.slice(0, start) + out.slice(end); });
fs.writeFileSync(file, out.replace(/\n{3,}/g, "\n\n"));
console.log(file + ": removed " + cuts.length);
