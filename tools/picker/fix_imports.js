const fs = require("fs");
const path = require("path");
const acorn = require("acorn");
const eslintScope = require("eslint-scope");

const root = process.argv[2] || path.join(__dirname, "..", "..", "boards", "editor", "picker");
const PART = /^\d\d_.*\.js$/;
const IMPORTS = /^(import \{[^}]*\} from "[^"]+";\n)+\n?/;

function partsUnder(dir) {
  return fs.readdirSync(dir).sort().flatMap(name => {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) return partsUnder(full);
    return PART.test(name) ? [full] : [];
  });
}

function parse(text) {
  const ast = acorn.parse(text, {ecmaVersion: 2022, sourceType: "module", ranges: true});
  const moduleScope = eslintScope.analyze(ast, {ecmaVersion: 2022, sourceType: "module"})
    .globalScope.childScopes[0];
  return {ast, moduleScope};
}

const parts = partsUnder(root);
const modules = {};
for (const file of parts) {
  const original = fs.readFileSync(file, "utf8");
  const exportedBefore = new Set([...original.matchAll(/^export (?:async )?(?:function\*? |var |let |const |class )([\w$]+)/gm)].map(found => found[1]));
  const text = original.replace(IMPORTS, "").replace(/^export (?=(async )?function|var |let |const |class )/gm, "");
  const {ast, moduleScope} = parse(text);
  const top = {};
  for (const node of ast.body) {
    if (node.type === "FunctionDeclaration" || node.type === "ClassDeclaration") top[node.id.name] = node;
    if (node.type === "VariableDeclaration") node.declarations.forEach(one => { top[one.id.name] = node; });
  }
  modules[file] = {text, top, exportedBefore, declared: new Set(moduleScope.variables.map(one => one.name)),
                   free: new Set(moduleScope.through.map(reference => reference.identifier.name))};
}

const owner = {};
for (const [file, one] of Object.entries(modules)) {
  for (const name of one.declared) {
    if (owner[name]) throw new Error(name + " is declared in " + owner[name] + " and " + file);
    owner[name] = file;
  }
}

const wanted = {};
for (const [file, one] of Object.entries(modules)) {
  one.imports = {};
  for (const name of one.free) {
    const from = owner[name];
    if (!from) continue;
    (one.imports[from] = one.imports[from] || new Set()).add(name);
    (wanted[from] = wanted[from] || new Set()).add(name);
  }
}

function importBlock(file, imports) {
  return Object.keys(imports).sort((a, b) => parts.indexOf(a) - parts.indexOf(b)).map(from => {
    let source = path.relative(path.dirname(file), from);
    if (!source.startsWith(".")) source = "./" + source;
    const names = [...imports[from]].sort();
    const line = "import {" + names.join(", ") + "} from \"" + source + "\";";
    if (line.length <= 100) return line;
    const rows = [];
    let row = " ";
    for (const name of names) {
      if ((row + " " + name + ",").length > 99) {
        rows.push(row);
        row = " ";
      }
      row += " " + name + ",";
    }
    rows.push(row.replace(/,$/, ""));
    return "import {\n" + rows.join("\n") + "\n} from \"" + source + "\";";
  }).join("\n");
}

const testsDir = path.join(__dirname, "..", "..", "tests", "picker");
const tested = new Set(fs.readdirSync(testsDir).filter(name => name.endsWith(".py"))
  .flatMap(name => fs.readFileSync(path.join(testsDir, name), "utf8").match(/[A-Za-z_$][\w$]*/g) || []));
for (const [file, one] of Object.entries(modules)) {
  for (const node of Object.values(one.top)) {
    if (node.type !== "FunctionDeclaration" && node.type !== "VariableDeclaration") continue;
    const names = node.id ? [node.id.name] : node.declarations.map(declared => declared.id.name);
    if (names.some(name => tested.has(name) && one.exportedBefore.has(name))) {
      (wanted[file] = wanted[file] || new Set()).add(names[0]);
    }
  }
}

let changed = 0;
for (const [file, one] of Object.entries(modules)) {
  let text = one.text;
  const starts = new Set();
  for (const name of wanted[file] || []) {
    const node = one.top[name];
    if (!node) throw new Error(path.relative(root, file) + ": " + name + " is used elsewhere but not declared at the top");
    starts.add(node.start);
  }
  [...starts].sort((a, b) => b - a).forEach(at => { text = text.slice(0, at) + "export " + text.slice(at); });
  const block = importBlock(file, one.imports);
  if (block) text = block + "\n" + (text.startsWith("\n") ? "" : "\n") + text;
  if (text !== fs.readFileSync(file, "utf8")) {
    fs.writeFileSync(file, text);
    changed++;
  }
}
console.log(changed + " of " + parts.length + " parts rewritten");
