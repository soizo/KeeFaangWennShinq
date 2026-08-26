# Kee Faang Wenn Shinq?

A static, single-page tool that checks whether your network can reach popular international websites (Google, YouTube, Twitter, Telegram, Instagram, GitHub, etc.).

Runs entirely in-browser — no server, no data collection.

## How It Works

Runs two browser-native checks per site in parallel: a `no-cors` request to the site's main page and a request for one known static asset. Either success marks the site accessible; failures are compared with the current-page baseline and other site results to distinguish **Unreachable** from **Unable to confirm**.

The automatic check uses a fixed five-second deadline. You can also test a custom domain independently; the page probes both its homepage and `/favicon.ico`, and accepts either a bare domain such as `example.com` or a full HTTP(S) URL.

The interface defaults to English and includes a Simplified Chinese option. English uses the period browser font stack, with the bundled `fonts/simsun.woff2` used as the Chinese fallback when a system SimSun/宋体 font is unavailable.

Browser security rules prevent inspecting cross-origin response content, so results indicate network reachability rather than guaranteeing that every page feature works.

## Deployment

Host the repository files anywhere static — GitHub Pages, Netlify, a simple HTTP server, or open `index.html` locally in a browser. Keep `connectivity.js` beside `index.html`.

## Licence

[MIT](./LICENCE)
