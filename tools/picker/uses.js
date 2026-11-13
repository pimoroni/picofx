const fs = require("fs");
const acorn = require("acorn");
const walk = require("acorn-walk");

const file = process.argv[2];
const text = fs.readFileSync(file, "utf8");
const ast = acorn.parse(text, {ecmaVersion: "latest", sourceType: "module"});
const imported = {};
const top = [];
for (const node of ast.body) {
  if (node.type === "ImportDeclaration") {
    for (const spec of node.specifiers) imported[spec.local.name] = node.source.value.replace(/^\.\//, "").replace(/\.js$/, "");
    continue;
  }
  const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
  const names = body.type === "VariableDeclaration" ? body.declarations.map(one => one.id.name)
    : body.id ? [body.id.name] : ["(statement@" + text.slice(0, node.start).split("\n").length + ")"];
  top.push({names, node, exported: node.type === "ExportNamedDeclaration"});
}
const own = new Set(top.flatMap(one => one.names));
for (const one of top) {
  const inside = new Set();
  const outside = new Set();
  walk.full(one.node, inner => {
    if (inner.type !== "Identifier" || one.names.includes(inner.name)) return;
    if (own.has(inner.name)) inside.add(inner.name);
    if (inner.name in imported) outside.add(imported[inner.name] + "." + inner.name);
  });
  const lines = text.slice(one.node.start, one.node.end).split("\n").length;
  console.log((one.exported ? "*" : " ") + one.names.join(",") + " [" + lines + "]  -> " + [...inside].join(" ") + "  || " + [...outside].join(" "));
}
