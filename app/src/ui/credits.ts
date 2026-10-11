import credits from "virtual:credits";
import type { Credits } from "./creditsData";
import { type StringKey, t } from "./strings";

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  text?: string,
  className?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className !== undefined) node.className = className;
  return node;
}

function section(titleKey: StringKey, id: string): { root: HTMLElement; list: HTMLUListElement } {
  const root = element("section");
  const heading = element("h3", t(titleKey));
  heading.id = id;
  root.append(heading);
  const list = element("ul");
  list.setAttribute("aria-labelledby", id);
  return { root, list };
}

/** Builds the credits dialog contents from the build-time data; separate from the DOM wiring. */
export function renderCredits(data: Credits, dialog: HTMLDialogElement): void {
  const title = element("h2", t("creditsTitle"));
  title.id = "credits-title";
  dialog.setAttribute("aria-labelledby", title.id);

  const body = element("div", undefined, "credits-body");
  body.tabIndex = 0;

  body.append(element("p", `${t("creditsCode")}: ${data.code}`));

  const sources = section("creditsSources", "credits-sources");
  for (const source of data.sources) {
    const item = element("li", `${source.attribution} — ${t("creditsLicence")}: `);
    const link = element("a", source.licence);
    link.href = source.licenceUrl;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    item.append(link);
    sources.list.append(item);
  }
  sources.root.append(sources.list);

  const approximations = section("creditsApproximations", "credits-approximations");
  approximations.root.append(element("p", t("creditsApproximationsNote")));
  for (const approximation of data.approximations) {
    const item = element("li");
    item.append(element("strong", `${approximation.title}:`), ` ${approximation.text}`);
    approximations.list.append(item);
  }
  approximations.root.append(approximations.list);

  const software = section("creditsSoftware", "credits-software");
  for (const entry of data.software) {
    software.list.append(element("li", `${entry.component} ${entry.version} — ${entry.licence}`));
  }
  software.root.append(software.list);

  body.append(sources.root, approximations.root, software.root);

  const close = element("button", t("creditsClose"), "credits-close");
  close.type = "button";
  close.autofocus = true;
  close.addEventListener("click", () => dialog.close());

  dialog.replaceChildren(title, body, close);
}

/**
 * Wires the "Créditos" button of index.html to a modal `<dialog>`: native focus trap, Escape to
 * close, focus back on the button, click on the backdrop to close.
 */
export function initCredits(): void {
  const opener = document.getElementById("credits-open");
  if (!(opener instanceof HTMLButtonElement)) {
    throw new Error("index.html is missing the #credits-open button.");
  }
  const dialog = element("dialog");
  dialog.id = "credits";
  renderCredits(credits, dialog);
  document.body.append(dialog);

  opener.setAttribute("aria-haspopup", "dialog");
  opener.addEventListener("click", () => dialog.showModal());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}
