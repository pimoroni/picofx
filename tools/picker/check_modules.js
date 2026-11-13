const fs = require("fs");
const path = require("path");
const acorn = require("acorn");
const eslintScope = require("eslint-scope");

const root = process.argv[2] || path.join(__dirname, "..", "..", "boards", "editor", "picker");
const PART = /^\d\d_.*\.js$/;
const IMPORT = /^import \{([^}]*)\} from "([^"]+)";\n/gm;

function partsUnder(dir) {
  return fs.readdirSync(dir).sort().flatMap(name => {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) return partsUnder(full);
    return PART.test(name) ? [full] : [];
  });
}

function analyse(file) {
  const text = fs.readFileSync(file, "utf8");
  const imports = {};
  for (const [, names, source] of text.matchAll(IMPORT)) {
    const from = path.normalize(path.join(path.dirname(file), source));
    for (const name of names.split(",").map(one => one.trim()).filter(Boolean)) imports[name] = from;
  }
  const ast = acorn.parse(text, {ecmaVersion: 2022, sourceType: "module", ranges: true});
  const scope = eslintScope.analyze(ast, {ecmaVersion: 2022, sourceType: "module"});
  const moduleScope = scope.globalScope.childScopes[0];
  const declared = new Set(moduleScope.variables.map(one => one.name).filter(name => !(name in imports)));
  const exported = new Set();
  for (const node of ast.body) {
    if (node.type !== "ExportNamedDeclaration" || !node.declaration) continue;
    const declaration = node.declaration;
    if (declaration.id) exported.add(declaration.id.name);
    (declaration.declarations || []).forEach(one => exported.add(one.id.name));
  }
  const free = new Set(moduleScope.through.map(reference => reference.identifier.name));
  const used = new Set();
  for (const variable of moduleScope.variables) if (variable.name in imports && variable.references.length) used.add(variable.name);
  return {imports, declared, exported, free, used};
}

const parts = partsUnder(root);
const modules = Object.fromEntries(parts.map(file => [file, analyse(file)]));
const owner = {};
for (const [file, one] of Object.entries(modules)) for (const name of one.declared) owner[name] = file;
const imported = new Set();
const problems = [];
const say = (file, words) => problems.push(path.relative(root, file) + ": " + words);
for (const [file, one] of Object.entries(modules)) {
  for (const name of one.free) if (owner[name]) say(file, name + " is " + path.relative(root, owner[name]) + "'s and not imported");
  for (const [name, from] of Object.entries(one.imports)) {
    if (!modules[from]) say(file, "imports " + name + " from a part that is not there");
    else if (!modules[from].exported.has(name)) say(file, "imports " + name + ", which " + path.relative(root, from) + " does not export");
    else imported.add(from + ":" + name);
    if (!one.used.has(name)) say(file, "imports " + name + " and never uses it");
  }
}
for (const [file, one] of Object.entries(modules)) for (const name of one.exported) if (!imported.has(file + ":" + name)) say(file, "exports " + name + ", which no part imports");
if (problems.length) {
  console.log(problems.join("\n"));
  process.exit(1);
}
console.log(parts.length + " parts, every import and export accounted for");
