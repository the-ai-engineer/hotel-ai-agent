export function message(container, role, text) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  container.append(node);
  node.scrollIntoView({ block: "nearest" });
  return node;
}

export function answer(node, result) {
  node.replaceChildren(document.createTextNode(result.answer));
  for (const source of result.sources || []) {
    if (!/^\/policies\/[a-z0-9-]+\?version=\d+$/.test(source.url)) continue;
    const link = document.createElement("a");
    link.href = source.url;
    link.textContent = source.title;
    link.target = "_blank";
    link.rel = "noopener";
    node.append(document.createElement("br"), link);
  }
}
