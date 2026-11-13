const fs = require("fs");
const path = require("path");
const acorn = require("acorn");
const walk = require("acorn-walk");

const entry = process.argv.slice(2).map(file => path.resolve(file));
const modules = {};

function load(file) {
  if (modules[file]) return modules[file];
  const ast = acorn.parse(fs.readFileSync(file, "utf8"), {ecmaVersion: "latest", sourceType: "module"});
  const one = modules[file] = {file, ast, imports: [], from: {}, functions: new Set()};
  for (const node of ast.body) {
    const declared = node.type === "ExportNamedDeclaration" ? node.declaration : node;
    if (declared && declared.type === "FunctionDeclaration") one.functions.add(declared.id.name);
    if (node.type !== "ImportDeclaration") continue;
    const source = path.resolve(path.dirname(file), node.source.value);
    one.imports.push(source);
    for (const spec of node.specifiers) one.from[spec.local.name] = source;
  }
  one.imports.forEach(load);
  return one;
}

entry.forEach(load);
const order = [];
const seen = new Set();
function visit(file) {
  if (seen.has(file)) return;
  seen.add(file);
  modules[file].imports.forEach(visit);
  order.push(file);
}
entry.forEach(visit);
const position = new Map(order.map((file, at) => [file, at]));

let problems = 0;
for (const file of order) {
  const one = modules[file];
  for (const node of one.ast.body) {
    const body = node.type === "ExportNamedDeclaration" ? node.declaration : node;
    if (!body || body.type === "FunctionDeclaration" || body.type === "ImportDeclaration") continue;
    walk.full(body, inner => {
      if (inner.type !== "Identifier" || !(inner.name in one.from)) return;
      const source = one.from[inner.name];
      if (position.get(source) < position.get(file) || modules[source].functions.has(inner.name)) return;
      problems++;
      console.log(path.relative(process.cwd(), file) + ":" + inner.name + " from " + path.basename(source));
    });
  }
}
console.log(order.map(file => path.basename(file)).join(" "));
process.exit(problems ? 1 : 0);
