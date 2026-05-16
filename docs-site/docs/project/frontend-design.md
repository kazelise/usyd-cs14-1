# Frontend Design

The frontend is split into two products that share the same backend: a researcher admin workspace and a participant survey runner.

## Admin Workspace

The admin UI is intentionally operational rather than decorative. Researchers need to create a study quickly, verify the participant experience, then export data.

Design principles:

- Put **Surveys** and **Analytics** in the primary navigation; remove unused areas such as Templates.
- Treat status filters as a real workflow: draft, published, closed.
- Keep export discoverable on Analytics because client review focuses on CSV/JSON evidence.
- Use stable forms and explicit controls for platform style, groups, languages, calibration, and tracking.
- Keep wording consistent around "survey workspace" and "research studies" rather than personal dashboard language.

## Participant Runner

The participant runner is where the social-media interface study happens. The same post/question data can render with different platform treatments through `platform_ui_style`.

Design principles:

- The runner must feel like the chosen platform family, not just change color.
- The survey controls must remain clear: language, progress, group, completion, and tracking status cannot disappear.
- The "More Information" link opens a new tab so participants do not lose the survey session.
- A floating attention widget shows whether face/eyes are detected and the current sample coverage.
- Mobile and desktop layouts must preserve readable posts and controls.

## Platform Style Treatments

| Style | Structural treatment |
| --- | --- |
| X / Twitter | Single timeline column with compact text-first cards and repost-style actions. |
| Facebook | Wider feed with blue social-card conventions and familiar engagement actions. |
| Instagram | Centered, image-forward cards with profile/story cues and square/portrait media. |
| Xiaohongshu | Masonry-style note grid with image-first cards and compact action chips. |
| Truth Social | Navy/red feed chrome with strong tab treatment and sharper card geometry. |
| Bluesky | Minimal two-tab feed chrome, soft sky palette, and rounded conversational cards. |
| Douyin / TikTok | Dark vertical-video inspired feed with immersive tall media and short-form action labels. |

## Why `platform_ui_style` Exists

`platform_style` is the older compatibility field used by the backend and legacy UI choices. `platform_ui_style` is the actual participant visual treatment, so newer styles such as Truth Social, Bluesky, and Douyin/TikTok can map back to compatible legacy values while still rendering a distinct participant experience.

