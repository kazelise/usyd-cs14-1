---
layout: home

hero:
  name: CS14 Research Platform
  text: Operations documentation
  tagline: A concise researcher-facing documentation site for building, testing, publishing, running, and exporting multilingual social-media survey studies.
  actions:
    - theme: brand
      text: Start Researcher Workflow
      link: /guide/researcher-workflow
    - theme: alt
      text: View MVP Matrix
      link: /project/acceptance-matrix

features:
  - title: Researcher Workflow
    details: Create surveys, compose social-media cards, manage blocks and questions, preview conditions, publish links, and run participants.
  - title: Data Operations
    details: CSV/JSON export guidance, survey/condition/language filters, translation import/export, and participant language selection.
  - title: Readiness Tracking
    details: PDF/MVP coverage matrix, local setup, live deployment operations, calibration troubleshooting, and privacy notes.
---

<div class="status-grid">
  <div class="status-tile">
    <strong>Live</strong>
    <span>Public demo deployment</span>
  </div>
  <div class="status-tile">
    <strong>10</strong>
    <span>PDF/MVP requirements mapped</span>
  </div>
  <div class="status-tile">
    <strong>3</strong>
    <span>Participant locales documented</span>
  </div>
</div>

<div class="doc-panel">

This site is separate from the application runtime and is intended for handover, marker review, and team coordination. It documents how the platform should be operated today and what must be checked before and during client demonstrations.

The public demo is live at [cs14.kazelis.top](https://cs14.kazelis.top/), with this documentation published separately at [cs14-docs.kazelis.top](https://cs14-docs.kazelis.top/). Both routes are served through Cloudflare Tunnel so the application can use standard HTTPS while the VM's port 443 remains reserved for another service.

<div class="tagline-row">
  <span>Survey builder</span>
  <span>Platform style gallery</span>
  <span>Translations</span>
  <span>Calibration</span>
  <span>Export</span>
</div>

</div>
