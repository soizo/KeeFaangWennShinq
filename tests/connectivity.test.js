const test = require("node:test");
const assert = require("node:assert/strict");
const Connectivity = require("../connectivity.js");

function fetchResult(ok) {
	return () =>
		ok
			? Promise.resolve({ type: "opaque" })
			: Promise.reject(new TypeError("network error"));
}

function imageResult(ok) {
	return () => {
		const image = { onload: null, onerror: null, _src: "" };
		Object.defineProperty(image, "src", {
			get: () => image._src,
			set: (value) => {
				image._src = value;
				if (value) {
					queueMicrotask(() => {
						if (ok && image.onload) image.onload();
						if (!ok && image.onerror) image.onerror();
					});
				}
			},
		});
		return image;
	};
}

function abortableFetch() {
	return (_url, options) =>
		new Promise((_resolve, reject) => {
			options.signal.addEventListener(
				"abort",
				() => {
					reject(new DOMException("Aborted", "AbortError"));
				},
				{ once: true },
			);
		});
}

test("baseline probe reports whether the current page responds", async () => {
	assert.equal(
		await Connectivity.probeUrl(
			"https://example.com",
			new AbortController().signal,
			fetchResult(true),
		),
		true,
	);
	assert.equal(
		await Connectivity.probeUrl(
			"https://example.com",
			new AbortController().signal,
			fetchResult(false),
		),
		false,
	);
});

test("homepage success marks the site reachable when its asset fails", async () => {
	const result = await Connectivity.probeSite(
		{ href: "https://example.com", url: "https://example.com/icon.png" },
		new AbortController().signal,
		{ fetch: fetchResult(true), createImage: imageResult(false) },
	);

	assert.equal(result, "reachable");
});

test("asset success marks the site reachable when its homepage fails", async () => {
	const result = await Connectivity.probeSite(
		{ href: "https://example.com", url: "https://example.com/icon.png" },
		new AbortController().signal,
		{ fetch: fetchResult(false), createImage: imageResult(true) },
	);

	assert.equal(result, "reachable");
});

test("both failed signals leave the site unclassified", async () => {
	const result = await Connectivity.probeSite(
		{ href: "https://example.com", url: "https://example.com/icon.png" },
		new AbortController().signal,
		{ fetch: fetchResult(false), createImage: imageResult(false) },
	);

	assert.equal(result, "failed");
});

test("aborting a pending probe settles it once and cleans up the image", async () => {
	let image;
	const createImage = () => {
		image = { onload: null, onerror: null, src: "" };
		return image;
	};
	const controller = new AbortController();
	const pending = Connectivity.probeSite(
		{ href: "https://example.com", url: "https://example.com/icon.png" },
		controller.signal,
		{ fetch: abortableFetch(), createImage: createImage },
	);

	const lateOnload = image.onload;
	controller.abort();
	assert.equal(await pending, "failed");
	lateOnload();
	assert.equal(await pending, "failed");
	assert.equal(image.onload, null);
	assert.equal(image.onerror, null);
	assert.equal(image.src, "");
});

test("new batches cancel old timers and reject stale completion", () => {
	const timers = new Map();
	let nextTimer = 0;
	const manager = Connectivity.createBatchManager({
		setTimeout: (callback, timeout) => {
			const id = ++nextTimer;
			timers.set(id, { callback: callback, timeout: timeout });
			return id;
		},
		clearTimeout: (id) => timers.delete(id),
	});

	const first = manager.start(5000);
	const second = manager.start(3000);
	assert.equal(first.controller.signal.aborted, true);
	assert.equal(timers.has(first.timer), false);
	assert.equal(manager.finish(first), false);
	assert.equal(manager.getActive().id, second.id);

	assert.equal(timers.get(second.timer).timeout, 3000);
	timers.get(second.timer).callback();
	assert.equal(second.controller.signal.aborted, true);
	assert.equal(manager.finish(second), true);
	assert.equal(manager.getActive(), null);
});

test("mixed raw results classify failed sites as unreachable", () => {
	assert.deepEqual(
		Connectivity.classifyResults(["reachable", "failed", "reachable"], false),
		["reachable", "unreachable", "reachable"],
	);
});

test("a reachable baseline classifies failed sites as unreachable", () => {
	assert.deepEqual(Connectivity.classifyResults(["failed", "failed"], true), [
		"unreachable",
		"unreachable",
	]);
});

test("no baseline and no reachable target produces unknown results", () => {
	assert.deepEqual(Connectivity.classifyResults(["failed", "failed"], false), [
		"unknown",
		"unknown",
	]);
});
