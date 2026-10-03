import { test } from "node:test";
import assert from "node:assert/strict";
import { decodeEvent, readEvents } from "../js/api.js";
test("SSE survives split UTF-8 and frame boundaries", async () => {
  const bytes = new TextEncoder().encode(
    'event: result\ndata: {"answer":"café"}\n\nevent: done\ndata: {}\n\n',
  );
  const body = new ReadableStream({
    start(c) {
      for (const byte of bytes) c.enqueue(new Uint8Array([byte]));
      c.close();
    },
  });
  const events = [];
  await readEvents({ body }, (e) => events.push(e));
  assert.equal(events[0].data.answer, "café");
  assert.equal(events[1].event, "done");
});
test("comments are ignored and multiline data is joined", () => {
  assert.equal(decodeEvent(": heartbeat"), null);
  assert.deepEqual(decodeEvent('event: x\ndata: {\ndata: "a":1}').data, {
    a: 1,
  });
});

test("non-success response is distinguishable from an uncertain network failure", async () => {
  const original = globalThis.fetch;
  const { request, ApiError } = await import("../js/api.js");
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ code: "conversation_busy" }),
  });
  try {
    await assert.rejects(
      request("/api/example", {}),
      (error) => error instanceof ApiError && error.status === 409,
    );
  } finally {
    globalThis.fetch = original;
  }
});
