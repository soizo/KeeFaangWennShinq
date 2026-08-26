# Kee Faang Wenn Shinq?

A static, single-page tool that checks whether your network can reach popular international websites (Google, YouTube, Twitter, Telegram, Instagram, GitHub, etc.).

Runs entirely in-browser — no server, no data collection.

## How It Works

Runs two browser-native checks per site in parallel: a `no-cors` request to the site's main page and a request for one known static asset. Either success marks the site accessible; failures are compared with the current-page baseline and other site results to distinguish **Unreachable** from **Unable to confirm**.

The automatic check uses a fixed five-second deadline. You can also test a custom domain independently; the page probes both its homepage and `/favicon.ico`, and accepts either a bare domain such as `example.com` or a full HTTP(S) URL.

The interface defaults to English and includes Simplified Chinese, Mainland-standard Traditional Chinese, Japanese, North Korean (`조선어`), Korean, and Vietnamese. The selected language is saved in the browser with `localStorage`.

`zh-Hant-CN` is generated directly from `zh-CN` by `python3 scripts/build-mainland-traditional.py`: OpenCC `s2t.json` runs first, then the Chinese-government-standard `t2gov.json`. `--check` verifies that the checked-in dictionary is exact. The script pins OpenCC 1.4.0 and government-standard repository commit `58fdb693db755cf060d4794514a9bc84b8e6ceeb`.

Period-appropriate local fonts are bundled as WOFF2 subsets: SimSun for Chinese; a patched Arial Black covering every precomposed and decomposed Vietnamese letter; Baekmuk Headline/Gulim/Dotum/Batang for Korean; and KwangMyeong/CheonRiMa/CheongPong for North Korean. Regenerate the Vietnamese and Hangul subsets with `python3 scripts/build-font-subsets.py`. The script requires fontTools 4.63.0 and verifies the exact local source-font SHA-256 hashes listed in the script before building.

Browser security rules prevent inspecting cross-origin response content, so results indicate network reachability rather than guaranteeing that every page feature works.

## Deployment

Host the repository files anywhere static — GitHub Pages, Netlify, a simple HTTP server, or open `index.html` locally in a browser. Keep `connectivity.js` beside `index.html`.

## Licence

[MIT](./LICENCE)
