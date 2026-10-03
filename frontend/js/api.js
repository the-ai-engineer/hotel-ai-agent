export class ApiError extends Error {
  constructor(code, status) {
    super(code);
    this.status = status;
  }
}

export async function request(path, body) {
  const response = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(error.code || "unavailable", response.status);
  }
  return response;
}

export function decodeEvent(block) {
  let event = "message";
  const data = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  return data.length ? { event, data: JSON.parse(data.join("\n")) } : null;
}

export async function readEvents(response, receive) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      let end;
      while ((end = buffer.indexOf("\n\n")) !== -1) {
        const event = decodeEvent(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
        if (event) receive(event);
      }
      if (done) return;
    }
  } finally {
    reader.releaseLock();
  }
}
