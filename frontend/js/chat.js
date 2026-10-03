import { ApiError, request, readEvents } from "./api.js";
import { message, answer } from "./render.js";
const $ = (selector) => document.querySelector(selector);
const messages = $("#messages");
let conversation;
let busy = false;
let pending;
const storageKey = "sanctuary-conversation";

async function initialize() {
  await request("/api/session", {});
  conversation = localStorage.getItem(storageKey);
  if (conversation) {
    try {
      const history = await (
        await request(`/api/conversations/${conversation}`)
      ).json();
      messages.replaceChildren();
      for (const turn of history.turns) {
        message(messages, "user", turn.message);
        const node = message(
          messages,
          "assistant",
          "This attempt did not complete.",
        );
        if (turn.result) answer(node, turn.result);
        if (turn.state === "running") {
          pending = turn.client_turn_id;
          await recover(node, pending);
        }
      }
      return;
    } catch (error) {
      if (!(error instanceof ApiError) || ![401, 404].includes(error.status))
        throw error;
      localStorage.removeItem(storageKey);
      message(
        messages,
        "assistant",
        "Your previous guest session has expired. Starting a new conversation.",
      );
    }
  }
  conversation = (await (await request("/api/conversations", {})).json()).id;
  localStorage.setItem(storageKey, conversation);
}
function setBusy(value) {
  busy = value;
  $("#chatForm button").disabled = value;
  $("#reset").disabled = value;
  $("#question").disabled = value;
}
async function recover(node, id) {
  try {
    const state = await (
      await request(`/api/conversations/${conversation}/turns/${id}`)
    ).json();
    if (state.result) {
      answer(node, state.result);
      pending = null;
      return;
    }
    node.textContent =
      state.state === "running"
        ? "Your answer is still being prepared."
        : "This attempt did not complete. Please try again.";
    if (state.state !== "running") {
      pending = null;
      return;
    }
  } catch (error) {
    if (error instanceof ApiError && [401, 404].includes(error.status)) {
      pending = null;
      node.textContent = "No saved attempt was found. Please try again.";
      return;
    }
    node.textContent = "We could not check this answer.";
  }
  const check = document.createElement("button");
  check.textContent = "Check result";
  check.onclick = () => recover(node, id);
  node.append(document.createElement("br"), check);
}
async function send(text) {
  if (busy || !text.trim()) return;
  if (pending) {
    message(
      messages,
      "assistant",
      "Check the previous answer before asking another question.",
    );
    return;
  }
  setBusy(true);
  let node;
  try {
    if (!conversation) await initialize();
    if (pending) {
      message(
        messages,
        "assistant",
        "Check the previous answer before asking another question.",
      );
      return;
    }
    message(messages, "user", text);
    node = message(messages, "assistant", "Looking into that…");
    const id = crypto.randomUUID();
    pending = id;
    const response = await request(`/api/conversations/${conversation}/turns`, {
      client_turn_id: id,
      message: text,
    });
    let complete = false;
    let partial = "";
    await readEvents(response, (event) => {
      if (event.event === "text_delta") {
        partial += event.data.text;
        node.textContent = partial;
      }
      if (event.event === "result") answer(node, event.data);
      if (event.event === "done") {
        complete = true;
        pending = null;
      }
      if (event.event === "error") {
        node.textContent = event.data.message;
        complete = true;
        pending = null;
      }
    });
    if (!complete) await recover(node, id);
  } catch (error) {
    if (node && error instanceof ApiError) {
      pending = null;
      node.textContent =
        error.status === 409
          ? "Another request is already running. Please wait and try again."
          : error.status === 401
            ? "Your guest session has expired. Start a new conversation."
            : error.status === 400
              ? "Please enter a question of up to 2,000 characters."
              : "The concierge is unavailable. Please try again.";
    } else if (node && pending) await recover(node, pending);
    else
      message(
        messages,
        "assistant",
        error.message === "invalid_input"
          ? "Please enter a question of up to 2,000 characters."
          : "The concierge is unavailable. Please contact the hotel.",
      );
  } finally {
    setBusy(false);
  }
}
async function open() {
  $("#chat").hidden = false;
  $("#launch").hidden = true;
  if (!conversation && !busy) {
    setBusy(true);
    try {
      await initialize();
    } catch {
      message(
        messages,
        "assistant",
        "The concierge is unavailable. Please contact the hotel.",
      );
    } finally {
      setBusy(false);
    }
  }
  $("#question").focus();
}
document.addEventListener("click", async (event) => {
  if (event.target.closest("[data-chat]")) await open();
  const ask = event.target.closest("[data-ask]");
  if (ask) {
    await open();
    send(ask.dataset.ask);
  }
  if (event.target.closest("[data-guide]")) {
    await open();
    send("What time can I check in?");
  }
});
$("#closeChat").onclick = () => {
  $("#chat").hidden = true;
  $("#launch").hidden = false;
  $("#launch").focus();
};
$("#chatForm").onsubmit = (event) => {
  event.preventDefault();
  const text = $("#question").value;
  $("#question").value = "";
  send(text);
};
$("#reset").onclick = async () => {
  if (busy) return;
  setBusy(true);
  localStorage.removeItem(storageKey);
  conversation = null;
  pending = null;
  messages.replaceChildren();
  try {
    await initialize();
  } catch {
    message(messages, "assistant", "The concierge is unavailable.");
  } finally {
    setBusy(false);
  }
};
$("#question").maxLength = 2000;
$("#chatWelcome").textContent =
  "Ask about arrival, breakfast or hotel policies.";
