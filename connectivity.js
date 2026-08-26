((root) => {
	function cacheBustedUrl(url) {
		var separator = url.indexOf("?") === -1 ? "?" : "&";
		return (
			url +
			separator +
			"_nc=" +
			Date.now() +
			"-" +
			Math.random().toString(36).slice(2)
		);
	}

	function probeUrl(url, signal, fetchFn) {
		return fetchFn(cacheBustedUrl(url), {
			mode: "no-cors",
			cache: "no-store",
			signal: signal,
		}).then(
			() => true,
			() => false,
		);
	}

	function probeImage(url, signal, createImage) {
		return new Promise((resolve) => {
			var image = createImage();
			var settled = false;

			function finish(reachable) {
				if (settled) return;
				settled = true;
				image.onload = null;
				image.onerror = null;
				signal.removeEventListener("abort", abort);
				if (!reachable) image.src = "";
				resolve(reachable);
			}

			function abort() {
				finish(false);
			}

			image.onload = () => {
				finish(true);
			};
			image.onerror = () => {
				finish(false);
			};
			signal.addEventListener("abort", abort, { once: true });

			if (signal.aborted) {
				abort();
				return;
			}

			image.src = cacheBustedUrl(url);
		});
	}

	function probeSite(site, signal, dependencies) {
		var fetchFn =
			dependencies && dependencies.fetch
				? dependencies.fetch
				: root.fetch.bind(root);
		var createImage =
			dependencies && dependencies.createImage
				? dependencies.createImage
				: () => new root.Image();

		return Promise.all([
			probeUrl(site.href, signal, fetchFn),
			probeImage(site.url, signal, createImage),
		]).then((signals) => (signals[0] || signals[1] ? "reachable" : "failed"));
	}

	function createBatchManager(timers) {
		var setTimer =
			timers && timers.setTimeout ? timers.setTimeout : root.setTimeout.bind(root);
		var clearTimer =
			timers && timers.clearTimeout
				? timers.clearTimeout
				: root.clearTimeout.bind(root);
		var active = null;
		var nextId = 0;

		return {
			start: function (timeout) {
				if (active) {
					clearTimer(active.timer);
					active.controller.abort();
				}

				var controller = new root.AbortController();
				var check = {
					id: ++nextId,
					controller: controller,
					timer: setTimer(function () {
						controller.abort();
					}, timeout),
				};
				active = check;
				return check;
			},
			finish: function (check) {
				if (!active || active.id !== check.id) return false;
				clearTimer(check.timer);
				active = null;
				return true;
			},
			getActive: function () {
				return active;
			},
		};
	}

	function classifyResults(results, baselineReachable) {
		var hasReachableEvidence =
			baselineReachable || results.indexOf("reachable") !== -1;
		return results.map((result) => {
			if (result === "reachable") return result;
			return hasReachableEvidence ? "unreachable" : "unknown";
		});
	}

	var api = {
		probeUrl: probeUrl,
		probeSite: probeSite,
		createBatchManager: createBatchManager,
		classifyResults: classifyResults,
	};

	root.Connectivity = api;
	if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis === "undefined" ? this : globalThis);
