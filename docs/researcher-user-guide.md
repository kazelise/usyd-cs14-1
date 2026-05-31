# Researcher User Guide

This guide covers the core workflow for building and running a social-media-interface survey in the CS14 platform.

## 1. Create a Survey

1. Sign in as a researcher.
2. Open `Admin -> Surveys -> Create Survey`.
3. Enter the study title and internal description.
4. Choose the participant feed style, such as X, Facebook, Instagram, Xiaohongshu, Truth Social, or Bluesky.
5. Set the number of participant groups for basic condition assignment.

New surveys enable click tracking, gaze tracking, and webcam calibration by default. Participants are randomly assigned to a configured group when they open the share link.

## 2. Add Social-Media Posts

1. Open the survey workspace.
2. Paste an article or social-media URL to create a post card.
3. Review the fetched title, image, description, and source label.
4. Override any display field needed for the study.
5. Set visible engagement counts, including likes, comments, and shares.
6. Add researcher-authored comment previews when needed.
7. Configure which participant groups can see the post, and optionally set group-specific engagement overrides.

The participant feed will use these post settings while storing participant interactions separately from the numbers shown to participants.

## 3. Add Survey Questions

Questions can be attached to a post or placed at the survey level. Supported question types include:

- Free text
- Single choice
- Multiple choice
- Likert
- Rating

Use the preview panel to check the participant-facing order before publishing.

## 4. Translate the Survey

The platform supports English, Simplified and Traditional Chinese, Japanese, Korean, and Spanish. Each survey enables a subset of these, and participants choose among the enabled languages.

1. Open the survey workspace translation panel.
2. Select the target language.
3. Export a JSON or CSV translation template.
4. Fill the translated fields.
5. Import the completed translation file.
6. Preview the target language before sending the share link.

## 5. Publish and Test

1. Publish the survey when the draft is ready.
2. Copy the generated share link.
3. Open the start page in a fresh browser session.
4. Confirm the consent checkbox.
5. Select the participant language.
6. Complete webcam calibration if required.
7. Review the feed, interact with posts, answer questions, and submit completion.

If the survey uses calibration, participants should use a desktop browser, allow camera access, and keep their face visible during the dot sequence.

## 6. Review Analytics and Export Data

Open `Admin -> Analytics` to review:

- Completion rate and average duration
- Group-level engagement differences
- Post-level clicks, likes, comments, and shares
- Calibration pass rate
- Quality flags such as very fast completions or low-interaction sessions

Use the export filters to download CSV or JSON datasets by participant group, language, response status, or calibration outcome. Exported participant identifiers are anonymized; raw participant tokens are not exposed in the export.
