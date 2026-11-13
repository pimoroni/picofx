import {currentText} from "./07_writing.js";

function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function paintLine(line) {
  var plain = escapeHtml(line);
  if (line.charAt(0) === "[") return "<span data-s='scene'>" + plain + "</span>";
  if (/^\s*#/.test(line)) return "<span data-s='comment'>" + plain + "</span>";
  var at = line.indexOf(":");
  if (at < 0) return plain;
  function settings(text) {
    return (text.match(/"[^"]*"|\S+|\s+/g) || []).map(function (token) {
      var pair = token.match(/^([^=\s]+)(=)(.*)$/);
      if (!pair) return escapeHtml(token);
      return "<span data-s='name'>" + escapeHtml(pair[1]) + "</span>" +
             "<span data-s='punc'>=</span>" +
             "<span data-s='value'>" + escapeHtml(pair[3]) + "</span>";
    }).join("");
  }
  var left = line.slice(0, at), right = line.slice(at + 1);
  var selector = left.match(/^(\s*)(\S+)(.*)$/);
  var head = selector
    ? escapeHtml(selector[1]) + "<span data-s='target'>" + escapeHtml(selector[2]) +
      "</span>" + settings(selector[3])
    : escapeHtml(left);
  var effect = right.match(/^(\s*)(\S+)(.*)$/);
  var tail = effect
    ? escapeHtml(effect[1]) + "<span data-s='effect'>" + escapeHtml(effect[2]) +
      "</span>" + settings(effect[3])
    : escapeHtml(right);
  return head + "<span data-s='colon'>:</span>" + tail;
}

var answered = {said: null, about: null};

function problemsIn(said) {
  var found = {};
  var at = null;
  (said || "").split("\n").forEach(function (line) {
    var named = line.match(/^line (\d+): ?(.*)$/);
    if (named) {
      at = Number(named[1]);
      (found[at] = found[at] || []).push(named[2]);
    } else if (at !== null && line.trim()) {
      found[at].push(line.trim());
    }
  });
  return found;
}

export function takeAnswer(said, about) {
  answered = {said: said || null, about: about};
  renderPreview();
}

export function renderPreview() {
  var problems = problemsIn(answered.said);
  var lines = currentText().split("\n");
  var read = (answered.about || "").split("\n");
  var changedSince = 0;
  var painted = lines.map(function (line, at) {
    var said = problems[at + 1];
    if (!said) return paintLine(line);
    if (read[at] !== line) {
      changedSince++;
      return paintLine(line);
    }
    return "<mark>" + paintLine(line) + "</mark><em>  " + escapeHtml(said.join(" ")) + "</em>";
  });
  Object.keys(problems).forEach(function (at) {
    if (Number(at) > lines.length) changedSince++;
  });
  document.getElementById("preview").innerHTML = painted.join("\n");
  var note = document.getElementById("previewNote");
  note.hidden = !changedSince;
  note.textContent = changedSince === 1 ? "One reported line has since changed."
                                        : changedSince + " reported lines have since changed.";
}
