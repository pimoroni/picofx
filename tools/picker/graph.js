const fs = require("fs");
const path = require("path");

const root = process.argv[2] || path.join(__dirname, "..", "..", "boards", "editor", "picker");

function partsUnder(dir) {
  return fs.readdirSync(dir).sort().flatMap(name => {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) return partsUnder(full);
    return /^\d\d_.*\.js$/.test(name) ? [full] : [];
  });
}

const edges = {};
const named = {};
for (const file of partsUnder(root)) {
  const text = fs.readFileSync(file, "utf8");
  edges[file] = [];
  for (const found of text.matchAll(/import \{([^}]*)\} from "([^"]+)"/g)) {
    const to = path.join(path.dirname(file), found[2]);
    edges[file].push(to);
    named[file + ">" + to] = found[1].split(",").map(name => name.trim()).filter(Boolean);
  }
}

let index = 0;
const stack = [];
const at = {};
const low = {};
const onStack = new Set();
const groups = [];
function connect(file) {
  at[file] = low[file] = index++;
  stack.push(file);
  onStack.add(file);
  for (const to of edges[file]) {
    if (!(to in at)) {
      connect(to);
      low[file] = Math.min(low[file], low[to]);
    } else if (onStack.has(to)) {
      low[file] = Math.min(low[file], at[to]);
    }
  }
  if (low[file] === at[file]) {
    const group = [];
    let one;
    do {
      one = stack.pop();
      onStack.delete(one);
      group.push(one);
    } while (one !== file);
    groups.push(group);
  }
}
Object.keys(edges).forEach(file => { if (!(file in at)) connect(file); });

const short = file => path.relative(root, file);
for (const group of groups.filter(group => group.length > 1)) {
  console.log("cycle of " + group.length + ": " + group.map(short).sort().join(" "));
  if (process.argv.includes("--edges")) {
    for (const from of group) for (const to of edges[from]) {
      if (group.includes(to)) console.log("  " + short(from).padEnd(26) + short(to).padEnd(26) + named[from + ">" + to].join(" "));
    }
  }
}
