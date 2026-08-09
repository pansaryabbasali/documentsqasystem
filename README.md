# Document Q&A System — Use Case Definition

> Portfolio project simulation. The organization below is fictional. All documents in
> [`dataset/`](dataset/) are synthetic content written for this project — no proprietary,
> client, or employer data is used anywhere in this repository.

## 1. The organization: Atlas Fluid Systems B.V.

**Atlas Fluid Systems** is a fictional mid-size industrial equipment manufacturer,
headquartered in Rotterdam, the Netherlands, founded in 1978.

| | |
|---|---|
| Headcount | ~3,200 employees |
| Annual revenue | ~€480M |
| Manufacturing plants | Rotterdam (NL), Gdańsk (PL), Pune (IN) |
| Service & support hubs | Rotterdam, Houston (US), Singapore |
| Products | Centrifugal & positive-displacement pumps, control valves, compressor packages |
| Customers | Refineries, municipal water/wastewater utilities, chemical processors, EPC contractors, power generation operators |

Atlas designs and manufactures fluid-handling equipment sold into industries where
unplanned downtime is extremely costly, so the equipment ships with extensive
documentation: installation/operation/maintenance (IOM) manuals, troubleshooting
guides, safety data sheets, standard operating procedures, and engineering change
notices — one set per product line, revised every time a component or spec changes.

The business unit sponsoring this initiative is **Global Technical Services (GTS)**,
which owns:

- **Field Service Engineering (FSE)** — ~220 engineers worldwide who install,
  commission, and repair equipment on customer sites.
- **Technical Support** — ~40 agents across Rotterdam and Houston handling ~5,000
  customer calls/month (spec questions, troubleshooting, warranty claims).
- **Internal Knowledge & Enablement** — HR policy, onboarding, and internal reporting
  content that every employee needs to self-serve.

## 2. Problem statement (Atlas-specific)

Atlas has accumulated roughly 15,000 pages of documentation across 40+ product lines,
spread across SharePoint, a legacy document management system, and regional shared
drives, with inconsistent naming and no shared taxonomy. In practice:

- **Field engineers lose time on-site.** An FSE re-torquing a pump casing or replacing
  a mechanical seal on a customer's shut-down line needs the exact spec or procedure
  in seconds, not after a 10-minute hunt through PDFs on a laptop with patchy plant
  Wi-Fi.
- **Support agents re-derive the same answers.** Many of the ~5,000 monthly calls are
  variations on questions already answered somewhere in an IOM manual, an SDS, or the
  warranty policy — agents currently keyword-search SharePoint and often miss the
  right document because callers don't use the same vocabulary as the manuals (e.g.
  a customer says "pump is screaming," the manual says "cavitation — NPSH deficit").
- **Institutional knowledge is siloed.** HR policies, onboarding material, and
  quarterly business reviews live in the same scattered state as technical docs,
  so even simple internal questions ("how many carry-over PTO days am I allowed")
  generate help-desk tickets instead of self-service answers.
- **Keyword search misses semantic intent.** SharePoint's native search is
  index-and-keyword based; it cannot connect a symptom description to the section of
  a manual that resolves it, or reconcile different terms for the same failure mode
  across product lines.

## 3. Enriched project scope

**Goal:** Pilot a system where GTS employees (field engineers, support agents, and
general staff) can upload/point the system at Atlas documentation and ask natural
-language questions, getting answers grounded in — and citable back to — the source
document and page/slide.

**Pilot scope** (deliberately bounded, not company-wide):

- One representative product family: the **AF-4500 pump series** (manuals,
  troubleshooting guide, SOP, spec sheet, SDS for its lubricant).
- A slice of internal/enterprise content that every GTS employee touches: HR
  policies, a quarterly business review deck, an onboarding deck, and an
  engineering change notice.

**Primary users & their questions:**

| Persona | Example question |
|---|---|
| Field Service Engineer | "What's the impeller wear ring clearance for the AF-4520?" |
| Technical Support Agent | "What lubricant does the AF-4500 series bearing housing use, and what's its flash point?" |
| Technical Support Agent | "What's covered under the standard warranty if a customer's pump failed after 14 months?" |
| New GTS employee | "How many PTO carry-over days am I allowed at Atlas?" |
| Regional manager | "What was EMEA's order backlog in Q2 2026?" |

**Success criteria for the pilot:**

- Every answer must cite the source document and page/slide — no ungrounded answers.
- The system must handle mixed document formats (PDF manuals/SDS, Word policies,
  PowerPoint decks, CSV spec sheets, plain-text memos) without a format-specific
  workaround for each one.
- Materially reduce time-to-answer versus manually searching SharePoint, measured
  against the example questions above.

*(Solution design and implementation are out of scope for this stage — this document
defines the use case and the pilot dataset only.)*

## 4. Dataset

All files under [`dataset/`](dataset/) are synthetic documents written for this
project, modeled on the kinds of documents Atlas's GTS org would actually produce.
They range from simple to moderately challenging — clean, text-native documents
with realistic structure (tables, numbered procedures, regulatory formatting,
mixed layouts), but without scanned/OCR artifacts or heavily visual layouts, which
are reserved for a separate, harder-document project.

| File | Format | Category | Difficulty |
|---|---|---|---|
| `product_manuals/AF-4500_Series_IOM_Manual.pdf` | PDF | Product manual | Medium |
| `product_manuals/AF-4500_Troubleshooting_Guide.pdf` | PDF | Product manual | Medium |
| `safety_and_compliance/SDS_AtlasHydraSeal_AH220.pdf` | PDF | Safety data sheet | Moderately challenging |
| `sops/SOP-114_Mechanical_Seal_Replacement.pdf` | PDF | Standard operating procedure | Simple–medium |
| `policies/Warranty_and_Service_Policy.pdf` | PDF | Policy | Simple |
| `support/Field_Service_FAQ.pdf` | PDF | FAQ | Simple |
| `policies/HR_Leave_and_Time_Off_Policy.docx` | DOCX | HR policy | Simple–medium |
| `policies/Expense_Reimbursement_Policy.docx` | DOCX | HR policy | Simple |
| `reports_and_presentations/Q2_2026_Business_Review.pptx` | PPTX | Business report | Moderately challenging |
| `reports_and_presentations/FSE_Onboarding_Overview.pptx` | PPTX | Onboarding deck | Simple–medium |
| `specifications/AF-4500_Series_Spec_Sheet.csv` | CSV | Structured spec data | Simple |
| `engineering/ECN-2031_Impeller_Material_Change.txt` | TXT | Engineering memo | Simple |

12 documents across 5 formats (PDF, DOCX, PPTX, CSV, TXT), spanning technical,
regulatory, procedural, HR, and business-reporting content.

## 5. Vendored dependencies

[`src/llm_gateway/`](src/llm_gateway/) is a vendored copy of the author's
**llm-gateway** package: a free-tier LLM gateway with automatic provider failover
(Groq → Gemini → OpenRouter), local quota tracking, and vision support. It is
copied in — not referenced — so this repository clones and runs standalone at
zero cost. All LLM calls in this project go through it; no provider SDK is used
directly. The gateway's own test suite (80 offline tests) and development history
live in its original repository.
