const fs = require("fs");
const path = require("path");
const acorn = require("acorn");
const walk = require("acorn-walk");

const args = process.argv.slice(2);
const apply = args.includes("--apply");
const down = args.includes("--down");
const files = args.filter(arg => !arg.startsWith("--"));
const decls = [];
for (const [index, file] of files.entries()) {
  if (!fs.existsSync(file)) continue;
  const text = fs.readFileSync(file, "utf8");
  const ast = acorn.parse(text, {ecmaVersion: "latest", sourceType: "module"});
  for (const node of ast.body) {
    if (node.type === "ImportDeclaration") continue;
    const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
    const names = body.type === "VariableDeclaration" ? body.declarations.map(one => one.id.name)
      : body.id ? [body.id.name] : [];
    const line = text.slice(0, node.start).split("\n").length;
    decls.push({file, index, names, node, line, lines: text.slice(node.start, node.end).split("\n").length,
                label: names.length ? names.join(",") : "@" + line, uses: new Set(), usedBy: new Set()});
  }
}
const owner = {};
decls.forEach(one => one.names.forEach(name => { owner[name] = one; }));
for (const one of decls) {
  walk.full(one.node, inner => {
    const to = inner.type === "Identifier" && owner[inner.name];
    if (to && to !== one) { one.uses.add(to); to.usedBy.add(one); }
  });
}
for (const one of decls) one.layer = one.index;
let changed = true;
while (changed) {
  changed = false;
  for (const one of decls) {
    const need = down ? Math.min(one.layer, ...[...one.usedBy].map(by => by.layer))
                      : Math.max(one.layer, ...[...one.uses].map(to => to.layer));
    if (need !== one.layer) { one.layer = need; changed = true; }
  }
}
let moved = 0;
const moves = {};
for (const one of decls) {
  if (one.layer === one.index) continue;
  moved += one.lines;
  const key = one.file + " -> " + files[one.layer];
  (moves[key] = moves[key] || []).push(one.names.length ? one.label : "@" + one.line);
}
if (!apply) {
  console.log(moved + " lines move");
  for (const key in moves) console.log("  " + key + ": " + moves[key].join(" "));
} else {
  const { execFileSync } = require("child_process");
  for (const key in moves) {
    const [from, to] = key.split(" -> ");
    execFileSync("node", [path.join(__dirname, "move.js"), from, to, ...moves[key]], {stdio: "inherit"});
  }
}
