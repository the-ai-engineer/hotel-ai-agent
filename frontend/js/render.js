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
  cards(node, result);
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

export function cards(node, result) {
  if (!result.availability || !result.cards?.length) return;
  const dates = document.createElement("p");
  const checked = new Date(result.availability.checked_at).toLocaleString();
  dates.textContent = `${result.availability.check_in} to ${result.availability.check_out} · ${result.availability.guests} guests. Checked ${checked} for this fictional hotel; no reservation made.`;
  node.append(dates);
  for (const villa of result.cards) {
    if (
      !/^[a-z0-9-]{1,80}$/.test(villa.slug) ||
      !/^\/assets\/[a-z0-9-]+\.(png|jpg|webp)$/.test(villa.image)
    )
      continue;
    const card = document.createElement("div");
    card.className = "villa-result";
    const image = document.createElement("img");
    image.src = villa.image;
    image.alt = `Fictional ${villa.name}`;
    const title = document.createElement("strong");
    title.textContent = villa.name;
    const description = document.createElement("p");
    description.textContent = villa.description;
    const link = document.createElement("a");
    link.href = `/villas/${villa.slug}`;
    link.textContent = "View villa";
    link.target = "_blank";
    link.rel = "noopener";
    card.append(image, title, description, link);
    node.append(card);
  }
}
