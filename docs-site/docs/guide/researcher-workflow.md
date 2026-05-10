# Researcher Workflow

This guide follows the normal study lifecycle: create a survey, add posts and question blocks, preview/test, publish, run participants, calibrate, and review analytics.

## Create Or Edit A Survey

1. Sign in as a researcher.
2. Open `Admin -> Surveys`.
3. Use `Create Survey` for a new study, or open an existing survey to edit it.
4. Enter the researcher-facing title and description.
5. Choose the participant feed style, such as X, Facebook, Instagram, Xiaohongshu, Truth Social, or Bluesky where available.
6. Configure the number of participant conditions/groups.
7. Decide whether click tracking, gaze tracking, and webcam calibration are required.
8. Save before adding detailed blocks or posts.

Use clear internal names for conditions, languages, and survey versions. That makes analytics filters and exports much easier to interpret later.

## Blocks And Question Types

Build the participant flow from blocks:

| Block type | Use |
|---|---|
| Post block | Shows a social-media-style card with title, source, image, engagement counts, comments, and optional More Information action. |
| Question block | Collects participant answers at survey level or under a specific post. |
| Instruction block | Gives short participant guidance between sections. |

Supported question types:

| Type | Good for | Researcher checks |
|---|---|---|
| Free text | Open-ended reasoning, explanation, recall. | Set required/optional state and keep prompts specific. |
| Single choice | One answer from a controlled list. | Ensure options are mutually exclusive. |
| Multiple choice | Multiple applicable categories. | Explain whether participants should choose all that apply. |
| Likert | Agreement, trust, perceived credibility. | Keep scale labels consistent across questions. |
| Rating | Numeric score or intensity. | Confirm min/max and labels match the study protocol. |

## Social-Media Post Template And Card Editor

1. Add a post block.
2. Paste a public article/page URL when metadata fetch is appropriate.
3. Review fetched title, description, image, and source label.
4. Override title, body text, image, source label, platform style, and visible engagement counts as needed.
5. Add researcher-authored comment previews when the study requires controlled comments.
6. Configure condition visibility and condition-specific overrides.
7. Set More Information button label/visibility if participants should be able to open the original article.
8. Preview the card in each target condition and language.

Displayed likes, comments, and shares are stimulus values. Participant interactions are recorded separately.

## Preview And Testing

Preview before publish:

1. Select a condition/group.
2. Select a participant language.
3. Review every block in participant order.
4. Confirm post cards, images, comments, counts, and More Information behavior.
5. Confirm required questions block completion as expected.
6. Run a fresh-browser participant test only after the preview is correct.

Preview or test sessions should be marked as preview data or excluded from final analytics/export. If the implementation does not yet guarantee this, record the test participant IDs and exclude them manually during analysis.

## Publish And Share

1. Publish only after content, translations, preview, and calibration settings are reviewed.
2. Copy the generated share link.
3. Send one share link to participants unless the study protocol intentionally separates cohorts.
4. Include the supported browser/device requirement when calibration is enabled.
5. Do not edit live survey wording during active data collection unless the protocol allows version changes.

## Participant Run

Participant path:

1. Open the share link.
2. Read the start page and consent statement.
3. Select language.
4. Allow camera access if calibration is enabled.
5. Complete the calibration guidance and dot sequence.
6. View the feed, interact with cards, open More Information where applicable, and answer questions.
7. Submit completion.

The participant language selection should be stored with the response and used for the rendered survey content. Condition assignment should remain stable if the participant refreshes or resumes.

## Calibration

Calibration should run before tracked feed interaction when enabled. A good run usually needs:

- Desktop or laptop browser.
- HTTPS in production, or localhost in local development.
- Camera permission allowed.
- Face visible, stable, and evenly lit.
- Participant looking at each dot rather than at the keyboard or another screen.

See [Calibration & Privacy](./calibration-privacy.md) for troubleshooting.

## Analytics And Export

Open `Admin -> Analytics` after participant runs. Check:

- Completion rate and session duration.
- Condition-level engagement differences.
- Post-level likes, comments, shares, clicks, and More Information opens.
- Calibration pass rate and quality bands.
- Suspicious-session flags such as very fast completion, empty responses, or duplicate comments.

For explicit CSV/JSON export instructions and filters, use [Data Export & Translations](./data-export.md).
