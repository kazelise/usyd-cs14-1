# CS14 Presentation Script and Q&A

This note is for the 10-minute stage update presentation, followed by a live demo.

## Slide 1

Good morning. This presentation is a stage update for the CS14 survey platform. I will not repeat the original PDF brief, because the client already understands the project scope. Instead, I will focus on what has improved since the last feedback session, and how the current system is ready for a repeatable public demo.

At this stage, we have a public app, public documentation, fixed demo share codes, and a stable demo survey. The main point is that the project is no longer only a development prototype. It is now packaged in a way that the client or examiner can open, test, and review.

## Slide 2

The demo flow I want to use is participant-first. The idea is simple: we generate evidence live, and then we inspect that evidence in the researcher dashboard.

So first, I will briefly show the documentation and demo access path. Then I will run through the participant survey, including calibration and feed interactions. After that, I will return to analytics and export, where we can see the response, calibration result, attention evidence, and interaction data. Finally, if time allows, I will quickly scan the different platform-style survey links.

## Slide 3

This slide shows the platform gallery. One important improvement is that the interface is not just one generic feed with different colors. The platform style now acts as a controlled research context.

For example, the X-style version is closer to a timeline, while Xiaohongshu and Douyin-style versions give a different visual rhythm. These are not official clones of the real platforms. They are research-oriented interface skins, designed to let researchers test how different social-media-style contexts may affect participant behaviour.

## Slide 4

This slide is about calibration and attention tracking. In the earlier version, the camera part worked, but the participant experience was not very clear. We improved this by making the webcam preview feel more natural, including a mirrored self-view.

During the survey, the participant can also see a small picture-in-picture tracking window. This makes the tracking status more transparent: the participant can tell whether the camera is active, whether the face and eyes are detected, and whether the signal is weak. The window is draggable, so it should not block the main survey content.

Importantly, this is not raw video storage. The system uses webcam signals to produce structured attention evidence, such as calibration quality, gaze samples, and confidence-related information.

## Slide 5

This slide explains why we use seeded stimuli for the demo. In a real research setup, the researcher needs control over the stimulus: the post source, headline, image, engagement numbers, comments, and survey question.

The seeded demo keeps these elements stable. That means the demo does not depend on whether an external website's metadata loads correctly at the moment of presentation. Also, the like, comment, and share numbers here should be understood as experimental stimuli, not as real popularity metrics from a live social platform.

## Slide 6

This slide connects analytics to exportable evidence. The main thing I want to explain here is not that the demo statistics are meaningful research findings. The important point is what kinds of data the system can collect and export.

The export includes participant and response identifiers, assigned group, language, completion status, calibration quality, attention confidence, answers, likes, shares, comments, click records, and per-sample gaze data. In CSV, each row can represent one gaze sample with timestamp, post ID, estimated screen X and Y, and iris coordinates, so researchers can inspect the attention timeline in spreadsheet tools. JSON keeps the same information in a nested structure.

## Slide 7

This slide is about documentation and handoff. Since this is a university project and also a research platform, the system needs to be understandable beyond the live demo.

The documentation explains the architecture, database design, API responsibilities, frontend structure, export fields, deployment preparation, and demo access. This is useful for the teacher, the client, and future developers. It also means the project can be reviewed even after the presentation, without relying only on what we show live.

## Slide 8

This slide is about honest boundaries. I think it is important to be clear about what the system does and does not claim.

The webcam workflow should still be demonstrated live by the presenter, because calibration quality depends on the actual camera environment. The analytics data in the demo should be explained as evidence from test runs, not as real study results. And the platform styles should be described as controlled research contexts, not official replicas of X, Instagram, Xiaohongshu, or other platforms.

This makes the system more credible, because we are showing the working product while keeping the research claims careful.

## Slide 9

This is the transition into the live demo. I will now open the browser and follow the real user path.

First, I will show the documentation page and where the demo access information is. Then I will open the main participant survey using the fixed demo code. I will go through the participant flow, including calibration, the feed, and interaction feedback. After that, I will switch to the researcher view to show analytics, export, and the data dictionary. If there is still time, I will quickly open a few gallery styles, especially X, Xiaohongshu, and Douyin, because they show the interface differences most clearly.

## Demo Talking Order

1. Open the documentation site and point to demo access and fixed share codes.
2. Open the main survey link with `CS14DEMO2026`.
3. Show participant flow: language, calibration, feed, action feedback, completion.
4. Open researcher analytics and explain response evidence.
5. Show CSV/JSON export and data dictionary.
6. Quickly show platform gallery links if time remains.

## 老师可能会问的问题

### 1. 这个项目现在是否满足原始 PDF 里的 MVP 要求？

可以回答：核心 MVP 已经覆盖。现在系统支持 researcher 创建和管理 survey，participant 完成 survey，平台风格 feed，camera calibration，基础 attention/gaze evidence，CSV/JSON export，多语言界面，以及公开部署和文档。仍然可以继续优化的是更细粒度的 time-series export、更强的数据可视化，以及更严谨的长期部署流程。

### 2. 你们现在导出的 CSV/JSON 里面到底有什么？

可以回答：导出包含 survey 和 response 层面的研究数据，例如 participant/response ID、group、language、completion status、answers、likes、shares、comments、click records、calibration quality、attention confidence 等。现在 CSV 也会把 gaze time-series 展开出来：每一行对应一个 gaze sample，包括 `timestamp_ms`、`post_id`、`screen_x`、`screen_y`、left/right iris 坐标和 server received time。JSON 则把这些 gaze samples 放在每个 response 下面的数组里。

### 3. 是否保存用户摄像头视频？

可以回答：不保存 raw video，也不上传原始摄像头画面。摄像头用于浏览器端的 face/eye detection 和 calibration，系统保存的是结构化结果，例如 calibration score、pass/fail、gaze samples、click records 和 confidence indicators。

### 4. 如果用户在做 survey 的时候离开画面，会发生什么？

可以回答：系统会通过 tracking status 和 gaze/face detection 状态反映质量变化。如果 face 或 eyes lost，attention confidence 会下降，gaze samples 会减少或出现缺口。现在 UI 也会通过 PiP 小窗让 participant 看到 tracking 状态。更细的 per-second confidence export 是后续增强方向。

### 5. 这个 gaze tracking 准确吗？能不能叫 eye tracking？

可以回答：我们会谨慎表述为 webcam-based attention or gaze evidence，而不是临床级或硬件级 eye tracking。它适合 MVP 阶段展示 calibration workflow、attention quality 和 interaction evidence，但不能过度宣称为高精度眼动仪。

### 6. 为什么要做不同 platform styles？

可以回答：这个项目的研究目标之一是 social-media-style interface studies。不同平台风格会影响 participant 如何阅读、点击、信任或互动。所以我们提供 X、Instagram、Xiaohongshu、Truth Social、Bluesky、Douyin 等 controlled interface contexts，让 researcher 可以在相同研究结构下比较不同 UI context。

### 7. 这些平台样式是不是官方复制？

可以回答：不是。我们不会把它描述成 official clone。它们是 research-oriented platform-style skins，用来模拟不同 social media interface patterns，例如 timeline、image-heavy feed、short-video-like card rhythm 等。这样既能满足研究需要，也避免过度品牌化或法律/伦理风险。

### 8. A/B test 或 group assignment 是怎么做的？

可以回答：participant 进入 survey 时会被分配到 group，研究者可以配置不同 group 可见的 posts 或 variants。analytics 和 export 里会保留 group 信息，所以后续可以按 group 比较 completion、clicks、engagement 和 calibration/attention quality。

### 9. 多语言支持到什么程度？

可以回答：系统支持 participant language selection，并且核心 UI 和 demo 内容已经按多语言流程处理。当前重点是展示 end-to-end multilingual pipeline：语言选择、翻译内容展示、RTL/LTR 方向支持，以及 export 里保留 language 字段，方便 researcher 后续按语言过滤和分析。

### 10. 为什么 demo 用 seeded posts，而不是实时抓 BBC/OpenAI 等网站？

可以回答：实时 Open Graph fetching 容易受到外部网站、网络状态、CORS、metadata 缺失影响。为了保证 client demo 稳定，我们准备了 seeded stimuli。研究者仍然可以配置真实链接和文章式内容，但演示时用 seeded data 可以保证每次看到一致的结果。

### 11. Analytics 页面上的数字能不能当研究结论？

可以回答：不能。demo analytics 只是为了证明系统可以记录和导出研究证据，不是为了证明某个 social media style 更有效。正式研究需要真实 participant sample、伦理审批、实验设计和统计分析。

### 12. 现在最大的限制是什么？

可以回答：最大的限制是 tracking 数据可视化还可以更强。现在系统已经记录 calibration、per-sample gaze XY、click records 和 interaction evidence，也可以导出 CSV/JSON。下一步应该把这些 time-series 数据做成更直观的 visual analytics，比如 attention over time、per-post gaze density 或 confidence trend。

### 13. 如果现场摄像头权限失败怎么办？

可以回答：我们会先尝试现场 calibration，因为这是最有说服力的 demo。如果浏览器权限或设备问题导致失败，可以使用 prewarmed completed response 作为 backup evidence，然后继续展示 analytics、export 和 gallery styles。这样不会让 demo 卡住。

### 14. 这个系统部署状态怎么样？

可以回答：当前有 public app 和 public docs，可以通过浏览器访问。对于课程展示和 client review 已经够用。长期生产部署还可以继续加强，例如更完整的 CI/CD、备份策略、监控和安全配置。

### 15. 如果后续继续做，最值得优先做什么？

可以回答：我会优先做三件事。第一，加入 detailed time-series export，让研究者可以下载按秒记录的 attention/click timeline。第二，增强 analytics 可视化，例如 group comparison chart、attention confidence trend、post-level interaction chart。第三，进一步打磨 platform style fidelity，让不同平台风格不仅颜色不同，而是布局和交互节奏也更明显。
