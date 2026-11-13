const fs = require("fs");
const path = require("path");
const acorn = require("acorn");
const walk = require("acorn-walk");

const files = process.argv.slice(2);
const decls = {};
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const ast = acorn.parse(text, {ecmaVersion: "latest", sourceType: "module"});
  for (const node of ast.body) {
    if (node.type === "ImportDeclaration") continue;
    const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
    const names = body.type === "VariableDeclaration" ? body.declarations.map(one => one.id.name)
      : body.id ? [body.id.name] : ["@" + path.basename(file) + ":" + text.slice(0, node.start).split("\n").length];
    const key = names.join(",");
    decls[key] = {key, names, node, file: path.basename(file), uses: new Set()};
  }
}
const owner = {};
for (const one of Object.values(decls)) one.names.forEach(name => { owner[name] = one.key; });
for (const one of Object.values(decls)) {
  walk.full(one.node, inner => {
    if (inner.type === "Identifier" && owner[inner.name] && owner[inner.name] !== one.key) one.uses.add(owner[inner.name]);
  });
}
let index = 0;
const at = {}, low = {}, stack = [], on = new Set(), groups = [];
function connect(key) {
  at[key] = low[key] = index++;
  stack.push(key); on.add(key);
  for (const to of decls[key].uses) {
    if (!(to in at)) { connect(to); low[key] = Math.min(low[key], low[to]); }
    else if (on.has(to)) low[key] = Math.min(low[key], at[to]);
  }
  if (low[key] === at[key]) {
    const group = [];
    let one;
    do { one = stack.pop(); on.delete(one); group.push(one); } while (one !== key);
    groups.push(group);
  }
}
Object.keys(decls).forEach(key => { if (!(key in at)) connect(key); });
for (const group of groups) {
  const filesIn = new Set(group.map(key => decls[key].file));
  if (filesIn.size > 1 || process.argv.includes("--all")) {
    console.log("group across " + [...filesIn].join(" ") + ": " + group.map(key => decls[key].file.slice(0, 2) + ":" + key).join(" "));
  }
}
