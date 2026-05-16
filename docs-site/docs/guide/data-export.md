# Data Export & Translations

This page gives explicit researcher instructions for CSV/JSON export, filtering, translation import/export, and participant language selection.

## Export CSV

1. Sign in as a researcher.
2. Open `Admin -> Analytics`.
3. Select the target survey.
4. Set filters before export:
   - Survey.
   - Condition/group.
   - Participant language.
   - Completion status.
   - Calibration outcome.
   - Preview/test-session inclusion if available.
5. Choose `CSV`.
6. Download the file.
7. Open it in a spreadsheet tool and confirm row count, column headers, and filter values.

Use CSV for statistical analysis, spreadsheet review, and sharing a flat dataset with supervisors.

## Export JSON

1. Sign in as a researcher.
2. Open `Admin -> Analytics`.
3. Select the target survey.
4. Apply the same survey, condition, language, completion, calibration, and preview filters.
5. Choose `JSON`.
6. Download the file.
7. Inspect the top-level survey metadata, response list, answers, interactions, calibration summaries, and tracking aggregates.

Use JSON when nested relationships matter, such as answers grouped under responses or post-level interaction bundles.

## Required Export Filters

| Filter | Why it matters | Example |
|---|---|---|
| Survey | Prevents mixing studies. | Export only `Misinformation Pilot A`. |
| Condition/group | Separates A/B stimulus variants. | Compare condition `1` against condition `2`. |
| Language | Keeps translated participant flows distinct. | Export only `zh` responses. |
| Completion status | Removes abandoned starts from final analysis. | Include completed responses only. |
| Calibration outcome | Separates high-quality tracking from poor calibration runs. | Include `good` and `acceptable`; review `poor`. |
| Preview inclusion | Prevents researcher tests from polluting analysis. | Exclude preview sessions by default. |

Exported participant identifiers should be anonymous. Raw participant tokens, passwords, camera video, and private authentication data should not appear in CSV or JSON exports.

## Translation CSV Export

1. Open the survey editor.
2. Go to the translations panel.
3. Select the target language, such as `zh` or `ar`.
4. Choose `Export CSV`.
5. Keep stable IDs unchanged.
6. Translate only the editable text fields.
7. Preserve CSV headers and encoding.

CSV is best for translators who work in spreadsheets.

## Translation CSV Import

1. Open the same survey translation panel.
2. Select the language matching the completed CSV.
3. Choose `Import CSV`.
4. Upload the completed template.
5. Review validation messages for missing IDs, invalid columns, or empty required fields.
6. Preview the survey in that language before publishing.

Do not manually invent IDs in the translation file. Export a fresh template if the survey structure changed.

## Translation JSON Export

1. Open the survey translation panel.
2. Select the target language.
3. Choose `Export JSON`.
4. Keep object IDs and keys unchanged.
5. Fill translated values in the expected fields.

JSON is best for structured review, developer inspection, and version control.

## Translation JSON Import

1. Open the survey translation panel.
2. Select the matching target language.
3. Choose `Import JSON`.
4. Upload the edited JSON file.
5. Resolve schema or missing-key errors.
6. Preview the target language.

## Participant Language Selection

Participants choose language on the start page before calibration and before the feed. The selected language should:

- Set the participant UI language.
- Set text direction where relevant, such as Arabic RTL.
- Determine translated survey title, instructions, posts, comments, and questions.
- Be stored on the survey response.
- Be available as an analytics/export filter.

If a translation is incomplete, researchers should either complete it before launch or clearly fall back to the default language according to the study protocol.

## Research CSV columns (flat file)

Each CSV row is **one participant response** (one session). Columns are fixed in this order. Several fields hold **JSON-encoded text** (arrays or objects) because the underlying data is nested; open them in Python/R with `json.loads` after reading the CSV.

| Column | Meaning |
| --- | --- |
| `survey_id` | Internal survey key. |
| `response_id` | Internal response key. |
| `participant_id` | Anonymised per-session id (hash-based; not the raw token). |
| `assigned_group` | A/B condition (1, 2, …). |
| `randomization_seed` | Server-side seed for stimulus ordering when used. |
| `shown_post_order` | JSON array of post ids as shown to the participant. |
| `is_preview` | `true` if this run was a researcher preview / test session. |
| `language` | Participant UI language code (e.g. `en`, `zh`, `ar`). |
| `response_status` | `completed`, `in_progress`, or `flagged`, etc. |
| `started_at` / `completed_at` | ISO timestamps. |
| **Calibration (flat)** | See below. |
| **Attention (flat)** | See below. |
| `gaze_count` | Number of **gaze samples** stored for this response (aggregate count; not raw xy time series in CSV). |
| `click_count` | Number of stored **click records** for this response. |
| `participant_interactions` | JSON array: likes, comments, dwell, **click_x / click_y**, `action_type`, timestamps. |
| `question_responses` | JSON array: question text, type, chosen answers / values. |
| `displayed_posts` | JSON array: post stimuli as seen for this participant’s group (title, URLs, engagement overrides). |

### Calibration fields in CSV

Flattened from the `calibration` object in JSON exports:

| CSV column | Interpretation |
| --- | --- |
| `calibration_status` | Workflow status (e.g. completed). |
| `calibration_quality` | Categorical quality tier (e.g. good / acceptable / poor). |
| `calibration_quality_score` | Numeric calibration score when available. |
| `calibration_passed` | `true`/`false` gate used by analytics filters and attention scoring. |

Detailed point-level calibration geometry is **not** repeated in every CSV row; session-level metrics above are what researchers use for inclusion rules and quality reporting.

### Attention-confidence fields in CSV

Flattened from the `attention` object. These summarise how consistently a face was tracked and how complete the attention window was **relative to calibration outcome**:

| CSV column | Typical use |
| --- | --- |
| `attention_confidence` | Overall confidence score for attention/face coverage. |
| `attention_quality` | Categorical bucket. |
| `attention_coverage` | Share of expected window with usable face/attention signal. |
| `attention_active_ms` | Active attention window duration. |
| `attention_expected_samples` / `attention_detected_samples` | Sample counts for coverage math. |
| `attention_missing_ms` | Time with missing signal. |
| `attention_no_face_periods` | Count of gaps without a face. |
| `attention_quality_reason` | Short machine-readable explanation for QA. |

See also [Attention confidence](./attention-confidence.md).

## JSON export shape

The JSON download wraps the same responses with **structured objects** instead of stringified JSON columns:

- `responses[].calibration` — object with `status`, `quality`, `quality_score`, `passed`, `face_detection_rate`, `stability_score`, `quality_reason`, `completed_at`.
- `responses[].attention` — object with the same keys as the `attention_*` CSV columns.
- `responses[].gaze_count` / `click_count` — aggregates matching CSV.
- Raw time-series gaze points are **not** inlined in the bulk export; counts and interaction/click records are the researcher-facing surface area in this schema.

Use JSON when you prefer nested objects without CSV string parsing; use CSV for spreadsheets and statistical packages.

## Planned Detailed Time-Series Export

The backend already stores timestamped gaze and click rows during the participant run. The current CSV/JSON export keeps the default download compact by exporting counts and response-level attention confidence, not every sample.

The next export improvement should add an optional **detailed time-series export** for studies that need second-by-second analysis:

1. Keep the normal CSV/JSON export as the default researcher download.
2. Add a separate “Detailed tracking export” action or query option so large files are requested intentionally.
3. Export gaze samples at the configured survey interval, normally `1000 ms` for demo studies.
4. Include `timestamp_ms`, `post_id`, `screen_x`, `screen_y`, iris coordinates when available, and matching click records with `target_element`.
5. Scope the export by survey, response status, group, language, and date range before download.
6. Prefer JSONL or zipped JSON/CSV for large studies instead of embedding all time-series rows inside each response object.
7. Continue excluding raw video, participant tokens, passwords, and browser session data.

This gives researchers a compact default export for normal review and an explicit high-volume export when they need replay-style analysis.
