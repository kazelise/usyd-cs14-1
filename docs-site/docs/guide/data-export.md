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
