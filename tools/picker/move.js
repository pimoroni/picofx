const fs = require("fs");
const acorn = require("acorn");

const [from, to, ...wanted] = process.argv.slice(2);
const text = fs.readFileSync(from, "utf8");
const ast = acorn.parse(text, {ecmaVersion: "latest", sourceType: "module"});
const lineOf = at => text.slice(0, at).split("\n").length;

const picked = ast.body.filter(node => {
  if (node.type === "ImportDeclaration") return false;
  const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
  const names = body.type === "VariableDeclaration" ? body.declarations.map(one => one.id.name)
    : body.id ? [body.id.name] : [];
  return names.some(name => wanted.includes(name)) || wanted.includes("@" + lineOf(node.start));
});
const found = new Set(picked.flatMap(node => {
  const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
  return [ "@" + lineOf(node.start) ].concat(body.type === "VariableDeclaration"
    ? body.declarations.map(one => one.id.name) : body.id ? [body.id.name] : []);
}));
const missing = wanted.filter(name => !found.has(name));
if (missing.length) {
  console.error("not found in " + from + ": " + missing.join(" "));
  process.exit(1);
}

const chunks = picked.map(node => text.slice(node.start, node.end));
let rest = text;
for (const node of picked.slice().reverse()) {
  let end = node.end;
  while (rest[end] === "\n") end++;
  rest = rest.slice(0, node.start) + rest.slice(end);
}
fs.writeFileSync(from, rest.replace(/\n{3,}/g, "\n\n").replace(/\n*$/, "\n"));
const movedNames = new Set(picked.flatMap(node => {
  const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
  return body.type === "VariableDeclaration" ? body.declarations.map(one => one.id.name) : body.id ? [body.id.name] : [];
}));
const unimported = text => text.replace(/^import \{([^}]*)\} from ("[^"]+");\n/gm, (all, names, source) => {
  const kept = names.split(",").map(name => name.trim()).filter(name => name && !movedNames.has(name));
  return kept.length ? "import {" + kept.join(", ") + "} from " + source + ";\n" : "";
});
const before = fs.existsSync(to) ? unimported(fs.readFileSync(to, "utf8")).replace(/\n*$/, "\n\n") : "";
fs.writeFileSync(to, before + chunks.join("\n\n") + "\n");
