Here is a detailed breakdown of **Epic 2 — Biodiversity Risk GIS Overlay** and everything required on the frontend, drawn directly from the Iteration 1 design report.

***

## Epic 2 Overview

Epic 2's purpose is to screen supplier locations against biodiversity-sensitive areas and environmental risk layers, returning a **single unified biodiversity risk profile** per supplier. It comprises three user stories: **US2.1** (overlay screening), **US2.2** (GIS layer configuration), and **US2.3** (threatened species detail). The frontend is built in **React TypeScript** and communicates with the FastAPI backend exclusively via RESTful API calls. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

***

## US2.1 — Biodiversity Risk Overlay View

This is the core map screen triggered after a user requests biodiversity screening for a supplier. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

**Required frontend components:**
- An **interactive map** that renders supplier pin locations with spatial context, showing which biodiversity-sensitive areas the supplier overlaps or is near (e.g., CAPAD protected area polygons, KBA boundaries)
- A **unified supplier risk profile card** that consolidates results from all five simultaneously-queried datasets (CAPAD, World KBA Database, ALA species data, EPBC SPRAT, and NVIS vegetation condition) into one readable output — not five separate map views [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/5310a64f-530a-4480-a622-5a47e5215a49/Open-Data-Integration.docx)
- When a user selects a supplier from the dashboard, a **detail drawer/panel** must open showing mapped location context and biodiversity overlap information [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- **Dual-mode indicators** — every risk result must use both text labels and visual indicators (e.g., icons, badges), never colour alone, to meet accessibility requirements [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

***

## US2.2 — GIS Layer Selection & Configuration

This screen allows users to choose which datasets are active before a screening run. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

**Required frontend components:**
- A **layer toggle panel** listing all available GIS datasets (CAPAD, World KBA, ALA, EPBC SPRAT, NVIS, Aqueduct Water Risk, etc.) with a short **plain-language description** for each — no GIS jargon [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- **Real-time layer enable/disable toggles** that feed into the screening request payload; deselected layers must be excluded from both the overlay computation and risk score calculation [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A **"save configuration" feature** so returning users are offered their previously saved layer set instead of the full default [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A **warning modal or inline alert** when the user tries to deselect mandatory regulatory layers (specifically CAPAD and EPBC SPRAT), explaining that removing them may affect disclosure completeness [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- Once results are returned, the UI must clearly **label which layers were active** in that run so results are traceable and reproducible [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

***

## US2.3 — Threatened Species Detail Panel

This is a drill-down panel accessible from within the biodiversity detail view for any screened supplier. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

**Required frontend components:**
- A **species list** showing all threatened species recorded within a configurable proximity radius of the supplier location, with each row displaying: common name, scientific name, EPBC listing category, and source dataset (ALA, GBIF, or SPRAT) [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A **species detail expandable row or side panel** — clicking a species shows its habitat type and any relevant notes from the SPRAT profile [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A **configurable radius input** (likely a slider or numeric input) so users can adjust the search proximity [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A well-designed **empty state** that explicitly states "no threatened species records found within this radius" — it must never render a blank or ambiguous screen [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)
- A **sort/filter control** allowing users to filter the species list by EPBC listing category: Critically Endangered, Endangered, or Vulnerable [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx)

***

## Cross-Cutting Frontend Requirements for Epic 2

These apply across all three US2.x screens: [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/5310a64f-530a-4480-a622-5a47e5215a49/Open-Data-Integration.docx)

| Requirement | Detail |
|---|---|
| **Tech stack** | React TypeScript; all data fetched via REST API from FastAPI backend |
| **Map library** | Must support GIS polygon/point overlays (e.g., Leaflet, Mapbox GL, or Deck.gl) |
| **Accessibility** | Text + visual indicators for all risk outputs — no colour-only status signalling |
| **No GIS expertise assumed** | All layer names, species data, and risk indicators must use plain language; EPBC listing status must be shown in full (not just numeric codes) |
| **Data attribution** | Source dataset labels (e.g., "ALA", "CAPAD 2024") must appear alongside every risk indicator in the UI |
| **Data-as-of date** | Each risk profile display must show a date stamp indicating the currency of the underlying datasets |
| **Explainable risk results** | Risk summaries should include a plain-language reason (e.g., "High risk: overlaps 2 KBAs, 14 threatened species within 5 km, medium location confidence") rather than just a score  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx) |
| **Mobile-friendly** | The persona (Mia) explicitly requires a screen-friendly, mobile-accessible interface with no GIS expertise required  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_39ccf637-82ba-41cc-9f16-edf7dd584f80/1b795aaa-9109-4241-a4bf-952547f49126/FIT5120_ITERARTION1_Report_IE.docx) |