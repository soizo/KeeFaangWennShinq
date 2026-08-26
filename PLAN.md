# 底层判断逻辑重写计划

## Context

当前项目是纯静态单页网络可达性检测工具，所有逻辑集中在 `index.html`，通过带缓存扰动参数的 favicon 图片请求判断 Google、YouTube、GitHub 等站点是否可达。用户希望提高底层判断的准确性与可靠性，同时保持现有 UI 风格不变。

目前已确认：

- 无服务端、无数据收集，部署边界应继续保持纯浏览器静态运行。
- 当前实现已有“同一站点多个 favicon URL 回退”的机制，但每站会并发请求默认 favicon、根 favicon 和两种 Apple touch icon；21 个站点会产生大量探测请求，且图标缺失、CDN 可达或站点限流都会污染结果。
- 当前 `probe` 把图片错误和超时都直接归为 `blocked`，无法区分“明确不可达”和“浏览器无法验证”。
- 当前自动检测与用户点击 3/5 秒按钮可重叠；旧批次会继续写入新批次 DOM，存在状态串线和错误总判定的竞态。
- 用户选择平衡假阳性与假阴性，并明确不要求继续基于 favicon；方案应优先检测站点入口而非图标资源。
- 用户接受第三种“无法确认”状态，以避免把浏览器安全策略、站点故障或网络超时硬判为封锁。
- 目标范围已确定为近两年的 Chrome、Safari、Firefox 和 Edge，可直接使用现代 `fetch`、`AbortController` 与 Promise，无需旧浏览器兼容层。
- 保留现有 3 秒/5 秒按钮和自动执行行为；所选时长作为整轮探测的统一截止时间，避免每个后备请求串行叠加等待。

## Approach

用户已选择浏览器内分层探测方案。以站点入口 URL 的浏览器原生 `fetch(..., { mode: "no-cors" })` 作为主要信号：请求完成即可证明浏览器建立了到目标站点的网络路径，但 opaque response 不提供状态码、响应头或正文，因此不能声称已验证页面内容。主页请求与该站点已配置的稳定静态资源并行探测；任一成功即为可达。两种信号都失败时，结合本轮基线请求与其他站点结果判断为不可达或无法确认。favicon 可继续作为显示图标或后备静态信号，但不再是唯一依据。

每次检测使用独立批次标识和统一 `AbortController`：主页与一个配置好的同站静态资源并行探测，任一成功即为可达；新一轮检测会取消旧轮，且只有当前批次可更新界面。整轮结束后，若某站两种信号均失败，但本页基线或其他站点成功，则标记不可达；若基线和全部站点都失败，则标记无法确认。保留现有 DOM 结构、文案层级和 Web 1.0 视觉样式，未知状态复用现有灰色样式，不新增依赖或服务端。

## Files to modify

- `connectivity.js`（新增）— 放置可独立测试的主页/静态资源探测、超时清理和三态聚合逻辑；以普通全局脚本暴露最小 API，继续支持直接打开静态文件。
- `index.html` — 保留 HTML/CSS 视觉结构；加载 `connectivity.js`，简化图标加载，并让 `runCheck` 负责批次取消与结果渲染。
- `tests/connectivity.test.js`（新增）— 使用 Node 22 内置 `node:test` 和手写 `fetch`/`Image` 假对象验证判断与竞态，不增加 package 或依赖。
- `README.md` — 把“仅 favicon 探测”更新为分层探测及三态结果说明。
- `PLAN.md` — 本实施计划。

## Reuse

- `index.html` 中现有 `sites[].href` 作为主页信号、`sites[].url` 作为后备静态资源及显示图标；删除动态猜测三个额外 icon 路径的 `getProbeUrls`，避免无效请求。
- 现有 3 秒/5 秒控制、表格行、状态 class、总体 verdict 容器及所有 CSS；未知结果复用 `status-checking` / `verdict-checking` 灰色外观。
- 浏览器原生 Promise、`fetch`、`AbortController`、`Image` 和计时器；Node 22 内置 `node:test`，不新增依赖或构建配置。
- MDN 明确：`no-cors` 跨域请求成功时只得到 opaque response（状态为 0、内容不可读）；网络失败会 reject，而 HTTP 4xx/5xx 本身不会让 `fetch` reject。`navigator.onLine` 不可靠，不作为判断依据。

## Steps

- [x] 明确规则：平衡假阳性/假阴性，允许“无法确认”，支持近两年主流浏览器，继续纯静态运行。
- [x] 新增失败测试：主页成功、主页失败但静态资源成功、双失败、统一超时、取消后迟到回调、混合结果、基线与全部目标均失败。
- [x] 在 `connectivity.js` 实现最小探测 API：两个信号并行、任一成功、统一截止、取消清理、结果只结算一次。
- [x] 实现纯聚合函数：`reachable` 保持可达；双失败且存在基线/其他成功为 `unreachable`；基线与全部目标均失败为 `unknown`。
- [x] 在 `index.html` 接入批次 ID 和 `AbortController`；开始新检测时取消旧批次，所有异步回调写 DOM 前检查批次 ID。
- [x] 保留现有表格和 verdict CSS；显示 `Accessible`、`Unreachable`、`Unable to confirm`，总体结论分别处理全通、部分、重度受限和无法确认。
- [x] 将站点图标加载缩减为每站一个已配置 URL，失败时显示现有 `broken.png`，不再动态猜测额外 favicon 路径。
- [x] 更新 README 的工作原理与限制说明。
- [x] 运行自动化与手工验证，确认 3/5 秒模式、重复点击、离线和单站拦截场景，并对比 UI 无视觉回归。

## Verification

- 运行 `node --test tests/connectivity.test.js`：所有分层探测、聚合、超时和取消用例通过；迟到的 `Image` 回调不得二次结算。
- 通过本地静态服务器打开页面，分别运行 3 秒和 5 秒检测；连续快速切换按钮，确认只显示最后一轮结果且无控制台异常。
- 使用浏览器 DevTools Offline：确认不误报“网络重度受限”，而显示“无法确认”。
- 使用 DevTools Request Blocking 阻止一个站点的主页和后备资源：其他站点可达时，该站显示 `Unreachable`，总体显示部分可达。
- 关闭 Request Blocking 后复测：该站任一信号成功即恢复 `Accessible`。
- 对比修改前后页面，确认 DOM 布局、字体、颜色、边框、图标尺寸和按钮交互风格不变。
- 直接以静态文件及 HTTP 静态托管各打开一次；确认无服务端、遥测、第三方库或构建步骤。
