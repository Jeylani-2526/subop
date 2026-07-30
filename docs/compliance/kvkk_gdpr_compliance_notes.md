# KVKK & GDPR Compliance Baseline Research
 
**Primary output:** Unified 10-item compliance checklist → specification input to M11 Security & Compliance module  
**Secondary output:** Regulatory requirement-to-module mapping → reference for Omer during M11 security specification design

---

## 1. Research Context — Why This Document Exists

SUBOP is designed to ingest, transform, route, and expose data across organisational systems. In any deployment where that data includes information about identifiable individuals — employees, customers, patients, citizens — the platform becomes a data processor under both KVKK and GDPR. The requirements these regulations impose are not optional features to add in Week 11: they are architectural constraints that must be baked into the design of multiple modules starting at M4.

This document serves two purposes:

1. **For the M2 Competitor Analysis and Feasibility Reports:** Confirms that SUBOP's planned G9 (Security & Compliance) is necessary and differentiated — none of the five tools in the comparison matrix provide full KVKK/GDPR coverage without significant external implementation effort.

2. **For M11 implementation planning (primary audience: Omer + Abdalla):** Every item in the 10-point checklist below maps to a specific SUBOP module, an implementation milestone, and a technical approach. Omer must use this document as the specification baseline when designing the M11 security module architecture. Any module that touches personal data (Connector Framework, ETL Engine, Metadata-Driven DW, Audit Log) must also account for the relevant checklist items before M11.

---

## 2. KVKK — Overview and Key Obligations

### 2.1 What KVKK Is

KVKK (Kişisel Verilerin Korunması Kanunu — Personal Data Protection Law) is Turkish Law No. 6698, enacted 7 April 2016 and phased into full effect through 2018. It was drafted in parallel with the EU GDPR and shares the same foundational principles — it was deliberately designed to align Turkey with EU data protection standards as part of Turkey's broader EU accession commitments.

**Supervisory authority:** KVKK Kurumu (Kişisel Verileri Koruma Kurumu — Personal Data Protection Authority), an independent administrative body headquartered in Ankara. The KVKK board issues binding decisions, administrative fines, and implementation guidelines.

**Who it applies to:** Any data controller (veri sorumlusu) or data processor (veri işleyen) that processes the personal data of Turkish natural persons, regardless of where that entity is located. If SUBOP processes data that includes Turkish residents' personal information, KVKK applies regardless of where the servers run.

### 2.2 Key Definitions

| Term | KVKK Definition |
|---|---|
| **Personal data (kişisel veri)** | Any information relating to an identified or identifiable natural person |
| **Special category data (özel nitelikli kişisel veri)** | Race/ethnicity, political opinion, religion, philosophical belief, appearance, union membership, health data, sexual life, criminal convictions, biometric data, genetic data — requires explicit consent or specific legal basis |
| **Data controller (veri sorumlusu)** | Natural or legal person who determines the purposes and means of processing |
| **Data processor (veri işleyen)** | Natural or legal person who processes data on behalf of the controller |
| **Explicit consent (açık rıza)** | Consent that is based on information, freely given, and specific to a defined purpose |

### 2.3 Core Principles (KVKK Article 4)

KVKK Article 4 requires personal data processing to comply with the following principles — these are the foundational constraints that flow through into SUBOP's pipeline design:

| Principle | Article | SUBOP Implication |
|---|---|---|
| Lawfulness and good faith | Art. 4(a) | All pipelines must have a documented lawful basis |
| Accuracy and currency | Art. 4(b) | ETL must not propagate stale or incorrect personal data |
| Processing for specified, explicit, and legitimate purposes | Art. 4(b) | Pipeline purpose must be declared in metadata |
| Relevance and data minimisation | Art. 4(d) | Connectors must extract only declared fields |
| Retention limited to purpose | Art. 4(e) | Warehouse must enforce retention policies per table |

### 2.4 Data Subject Rights (KVKK Article 11)

Data subjects in Turkey have the right to:
- Know whether their personal data is being processed
- Request information about processing if their data is being processed
- Know the purpose of processing and whether data is used in accordance with that purpose
- Know third parties to whom data is transferred domestically or internationally
- Request rectification of incomplete or incorrect data
- Request erasure or destruction under the conditions in Article 7
- Request notification to third parties of rectification or erasure actions
- Object to any result that arises against them from automated analysis of their data
- Demand compensation for damage suffered due to unlawful processing

SUBOP must implement an API surface to handle all of these requests against its warehouse data.

### 2.5 VERBİS Registration (KVKK-Specific)

Controllers not exempt from registration must register their data processing activities in VERBİS (Veri Sorumluları Sicil Bilgi Sistemi — Data Controllers Registry Information System). This registration discloses: purpose of processing, data subject categories, data categories, planned retention periods, and data recipients. Pilot organisations using SUBOP may have VERBİS registration obligations that the SUBOP compliance documentation must help support (pre-defined templates for purpose declarations, retention periods, and data categories).

### 2.6 Penalties

| Violation | Administrative Fine Range |
|---|---|
| Failure to fulfil disclosure obligation (Art. 10) | 5,000 – 100,000 TRY |
| Unlawful processing of personal data | 50,000 – 1,000,000 TRY |
| Failure to take security measures (Art. 12) | 15,000 – 1,000,000 TRY |
| Failure to notify data breach | 25,000 – 2,000,000 TRY |
| Failure to comply with KVKK board decision | 25,000 – 1,000,000 TRY |
| Criminal penalties | Under Turkish Penal Code Articles 135–140 |

---

## 3. GDPR — Overview and Key Obligations

### 3.1 What GDPR Is

GDPR (General Data Protection Regulation) is EU Regulation 2016/679, effective 25 May 2018. It is the global benchmark for data protection law and has directly influenced KVKK, Brazil's LGPD, California's CCPA, and dozens of other national regulations.

**Supervisory authorities:** National Data Protection Authorities (DPAs) in each EU member state — for example, CNIL (France), BfDI (Germany), ICO (United Kingdom after Brexit), APD (Belgium). The European Data Protection Board (EDPB) coordinates consistency across member states.

**Who it applies to:** Any organisation that processes personal data of EU or EEA residents, regardless of where the organisation is located. **Extraterritorial scope is explicit in Article 3.** If SUBOP is deployed by an organisation serving EU residents, GDPR applies even if the servers are in Turkey.

**Important for SUBOP:** The majority of SUBOP's planned pilot organisations are expected to handle data subject to both KVKK and GDPR — a university managing student records (Turkish students with EU study exchanges), a logistics company handling EU customer orders, or a healthcare organisation serving cross-border patients.

### 3.2 Core Principles (GDPR Article 5)

| Principle | Article | SUBOP Implementation Requirement |
|---|---|---|
| Lawfulness, fairness, transparency | Art. 5(1)(a) | Legal basis documented per dataset; audit log for all data access |
| Purpose limitation | Art. 5(1)(b) | Pipeline DSL must capture and enforce stated processing purpose |
| Data minimisation | Art. 5(1)(c) | Connector field declarations; no SELECT * for personal data tables |
| Accuracy | Art. 5(1)(d) | Data quality module detects and flags inaccurate personal data |
| Storage limitation | Art. 5(1)(e) | Retention policy per warehouse table; automated erasure on expiry |
| Integrity and confidentiality | Art. 5(1)(f) | TLS in transit, encryption at rest for sensitive columns, RBAC |
| Accountability | Art. 5(2) | Full audit trail; GDPR-ready compliance documentation |

### 3.3 Lawful Basis for Processing (GDPR Article 6)

Every processing activity must have one documented lawful basis:

| Basis | When applicable for SUBOP |
|---|---|
| **Consent** | Where the data subject has explicitly agreed to specific processing |
| **Contract** | Where processing is necessary to perform a contract with the data subject |
| **Legal obligation** | Where processing is required by law (e.g., tax records, employee data) |
| **Vital interests** | Where processing is necessary to protect life |
| **Public task** | Where processing is in the public interest (universities, public bodies) |
| **Legitimate interests** | Where the controller has a legitimate interest that is not overridden by the data subject's rights |

SUBOP's metadata layer (G5 — Metadata-Driven DW, M8) must store the lawful basis as a mandatory field per dataset. Pipelines processing personal data without a documented basis are non-compliant by design.

### 3.4 Data Subject Rights (GDPR Articles 15–22)

| Right | Article | SUBOP Technical Requirement |
|---|---|---|
| Right of access | Art. 15 | GET /compliance/subject/{id}/data — returns all personal data records |
| Right to rectification | Art. 16 | PATCH /compliance/subject/{id} — corrects inaccurate records across tables |
| Right to erasure | Art. 17 | DELETE /compliance/subject/{id} — cascades across warehouse + CDC log |
| Right to restriction | Art. 18 | is_restricted flag on subject identity; restricted records excluded from downstream analytics |
| Right to portability | Art. 20 | GET /compliance/subject/{id}/export?format=json|csv — machine-readable export |
| Right to object | Art. 21 | Objection flag; removes subject from automated pipeline processing |

### 3.5 Privacy by Design & Default (GDPR Article 25)

Article 25 is a **proactive architectural requirement**, not a reactive compliance check. It requires that data protection is embedded into systems at the design stage and that privacy-protective defaults are applied:

- **By design:** SUBOP must implement RBAC, column masking, and minimum data access policies as core architectural features — not as optional add-ons configurable post-deployment
- **By default:** Without explicit configuration to the contrary, pipelines must apply minimum data collection (data minimisation) and minimum data retention (storage limitation) by default

This requirement directly validates SUBOP's planned RBAC (M11), column masking (M11), and retained field declarations in the Connector Framework (M4).

### 3.6 Data Breach Notification (GDPR Articles 33–34)

- **Article 33:** Controller must notify the supervisory DPA within **72 hours** of becoming aware of a personal data breach, unless the breach is unlikely to result in risk to individuals' rights and freedoms.
- **Article 34:** Controller must notify data subjects **without undue delay** when the breach is likely to result in **high risk** to their rights and freedoms.

SUBOP's Audit Log module must: (a) generate a timestamped breach_event record the moment an anomalous access or data loss event is detected; (b) include a notification workflow template that the compliance officer can use to file the DPA notification within the 72-hour window.

### 3.7 Data Protection Impact Assessment (GDPR Article 35)

A DPIA is mandatory when processing is likely to result in high risk to the rights and freedoms of natural persons — specifically when using automated processing for decisions that significantly affect individuals (e.g., profiling), processing special categories of data at scale, or systematic monitoring of public areas.

SUBOP's ML-based anomaly detection prototype (part of G7, M10) may trigger DPIA requirements. The compliance documentation delivered in M12 must include DPIA templates for the high-risk processing scenarios a pilot organisation might run on top of SUBOP.

### 3.8 Penalties

| Tier | Maximum Fine | Examples |
|---|---|---|
| **Lower tier** | €10 million or 2% of global annual turnover (whichever is higher) | Breach notification failures; processor obligations |
| **Higher tier** | €20 million or 4% of global annual turnover (whichever is higher) | Principles of processing; data subject rights; cross-border transfers |

---

## 4. Key Differences — KVKK vs. GDPR

| Topic | KVKK | GDPR |
|---|---|---|
| **Jurisdiction** | Turkey | EU/EEA + extraterritorial (Art. 3) |
| **Effective date** | April 2016 (phased enforcement from 2018) | May 2018 |
| **Controller registration** | VERBİS registration required (unless exempt) | No equivalent registration requirement |
| **DPO requirement** | Not required by law (KVKK guidelines recommend) | Required for public bodies, large-scale processing, or special category data (Art. 37) |
| **Cross-border transfers** | Restricted; requires adequate protection finding by KVKK board or explicit consent | Restricted; adequacy decision, SCCs, BCRs, or binding consent |
| **DPIA** | No formal statutory mandate; KVKK board issues guidance | Mandatory for high-risk processing (Art. 35) |
| **Breach notification** | 72 hours to KVKK; data subjects "as soon as possible" | 72 hours to DPA (Art. 33); data subjects without undue delay if high risk (Art. 34) |
| **Penalties** | 5,000 – 2,000,000 TRY + criminal sanctions | Up to €20M or 4% global annual turnover |
| **SUBOP relevance** | Applies to all Turkish pilot organisations; most likely use case | Applies to pilots with EU customers, EU-resident employees, or cross-border operations |

**Practical implication for SUBOP pilots:** Most realistic pilot organisation profiles — a Turkish university with Erasmus students, a logistics company with EU customers, a healthcare provider — will be subject to **both** regulations simultaneously. SUBOP's compliance module must satisfy both frameworks. Where they differ, SUBOP must implement the stricter requirement (typically GDPR for the quantitative dimensions, KVKK's VERBİS documentation for the registration dimension).

---

## 5. SUBOP Processing Context — What Data May Flow Through the Platform

Before mapping requirements to modules, it is essential to identify where personal data is likely to appear in a SUBOP pipeline:

| Data Category | Likely Source | SUBOP Entry Point | Applicable Regulation |
|---|---|---|---|
| Employee records (name, ID, salary, contract) | HR ERP systems (SAP, Dynamics) | Connector Framework | Both |
| Customer records (name, email, address, purchase history) | CRM systems (Salesforce, custom) | Connector Framework | Both (GDPR if EU customers) |
| Student records (name, ID number, academic results) | University SIS (student information systems) | Connector Framework | Both |
| Patient records (name, TC ID, diagnosis, medication) | Hospital information systems | Connector Framework | Both (special category) |
| IoT/device data (if device linked to individual) | IoT streaming sources | Kafka CDC Module | Both (if identifiable) |
| Financial transaction data | ERP/banking systems | Connector Framework | Both |
| System access logs (username, IP, timestamp) | Application databases | CDC pipeline | Both (if user identifiable) |

SUBOP is not inherently a personal data processor — it becomes one when a pipeline is configured to extract tables containing personal data. The compliance module must ensure that **all pipelines are classified** at configuration time as either: (a) personal data pipeline — full compliance controls active, or (b) non-personal data pipeline — standard controls only.

---

## 6. Unified Compliance Checklist — KVKK & GDPR

*This is the primary output of this research document. It constitutes the specification input to the M11 Security & Compliance module. Omer must implement a technical solution for each item below.*

| # | Requirement | Framework | SUBOP Module Responsible | Implementation Milestone |
|---|---|---|---|---|
| **C01** | **Data Minimisation** — Only personal data necessary for the stated processing purpose may be collected and processed. Pipelines must declare which fields they extract; default extraction must not be SELECT *. | Both (KVKK Art. 4(d) / GDPR Art. 5(1)(c)) | Connector Framework (G2) | **M4** |
| **C02** | **Purpose Limitation** — Every personal data pipeline must have a declared processing purpose stored in the pipeline metadata. Processing must not extend beyond the declared purpose without a new lawful basis. | Both (KVKK Art. 4(b) / GDPR Art. 5(1)(b)) | ETL Engine (G3) · Metadata-Driven DW (G5) | **M5 / M8** |
| **C03** | **Lawful Basis Documentation** — Every dataset containing personal data must have a documented lawful basis (consent, contract, legal obligation, legitimate interest, or equivalent). Basis must be stored as a mandatory metadata field per table in the warehouse. | Both (KVKK Art. 5–6 / GDPR Art. 6) | Metadata-Driven DW (G5) | **M8** |
| **C04** | **Explicit Consent Tracking** — Where the lawful basis is consent, the platform must record and maintain evidence of consent (data subject identity, purpose, timestamp, consent version). Consent revocation must propagate to all pipeline executions and stored records associated with the subject. | Both (KVKK Art. 3/5 / GDPR Art. 7) | Security & Compliance (G9) | **M11** |
| **C05** | **Data Subject Rights — Access, Rectification, Restriction, Objection** — The platform must provide an API surface to fulfil data subject requests: access (retrieve all personal data records for a subject), rectification (correct inaccurate records across all warehouse tables), restriction (flag records to exclude from downstream analytics), and objection (remove subject from automated pipeline scope). | Both (KVKK Art. 11 / GDPR Art. 15, 16, 18, 21) | Security & Compliance (G9) | **M11** |
| **C06** | **Right to Erasure (Right to Be Forgotten)** — Personal data must be erased when no longer necessary for the purpose it was collected, when consent is withdrawn, or upon a verified data subject erasure request. Erasure must cascade across warehouse tables, the CDC event log, and all derived outputs. Audit trail records must be anonymised (not deleted) to preserve regulatory accountability. | Both (KVKK Art. 7 / GDPR Art. 17) | Security & Compliance (G9) · Metadata-Driven DW (G5) | **M8 (retention) / M11 (API)** |
| **C07** | **Right to Data Portability** — Where processing is based on consent or contract and carried out by automated means, the platform must provide a data subject export endpoint that returns all personal data associated with the subject identity in a structured, machine-readable format (JSON and/or CSV minimum). | Both (KVKK Art. 11(f) / GDPR Art. 20) | Connector Framework (G2) · Security & Compliance (G9) | **M6 (export endpoint) / M11 (compliance API)** |
| **C08** | **Personal Data Breach Notification — 72-Hour Window** — The platform must include a breach detection and notification mechanism. Audit Log must generate a timestamped breach_event record immediately upon detection of an anomalous data access or loss event. The platform must provide a notification workflow template enabling the organisation's compliance officer to file the required DPA notification within 72 hours. Data subjects must be notified where the breach poses high risk to their rights. | Both (KVKK Art. 12 / GDPR Art. 33–34) | Security & Compliance (G9) · Audit Log | **M11** |
| **C09** | **Data Retention Limits (Storage Limitation)** — Personal data must not be retained in identifiable form for longer than necessary. The warehouse schema must enforce a retention_policy_days field per table. An automated scheduled job must anonymise or delete records that have exceeded their declared retention period. Retention periods must be documented in the data catalog. | Both (KVKK Art. 4(e) / GDPR Art. 5(1)(e)) | Metadata-Driven DW (G5) · Data Catalog (G8) | **M8** |
| **C10** | **Privacy by Design & Data Security** — Technical and organisational measures must ensure that only the minimum necessary personal data is processed by default. Access must be governed by role-based access control (RBAC) with a deny-by-default policy. Sensitive columns must be masked at query time based on user role. All inter-module connections must use TLS. The architecture must implement privacy-protective defaults from the first deployed version (M3), with full enforcement in M11. | Both (KVKK Art. 12 / GDPR Art. 25 + Art. 32) | Platform-wide (all modules) · Security & Compliance (G9) primary enforcement | **M3 (architecture) / M11 (full enforcement)** |

---

## 7. SUBOP Module Implementation Map

This section organises the checklist requirements by module — the view Omer needs when designing each module's compliance surface.

### Connector Framework (G2 — M4)
- **C01:** Add `declared_fields: [list]` to `ConnectionConfig`; connector must extract only listed fields. Raise `ComplianceError` if `declared_fields` is empty for a table flagged as `personal_data: true`.
- **C07:** Implement a subject data export method: `export_subject_data(subject_id, format='json')` returning all records associated with the subject across all connected sources.

### ETL Engine (G3 — M5)
- **C02:** Pipeline DSL must include a required `processing_purpose` field. ETL job metadata stored in the execution log must carry this field on every run. Purpose mismatch detection (pipeline attempting to use personal data for a purpose not declared in C03's lawful basis) should raise a compliance warning.

### Metadata-Driven Data Warehouse (G5 — M8)
- **C03:** Add mandatory `legal_basis` field to the warehouse table schema specification. Enum: `Consent | Contract | LegalObligation | VitalInterests | PublicTask | LegitimateInterest`. Validation at schema creation must reject tables containing personal data without a declared basis.
- **C06 (retention side):** Add `retention_policy_days` field to warehouse table schema. Create a scheduled retention enforcement job that runs nightly: identifies expired personal data records and anonymises or deletes them per the table's configured erasure strategy.
- **C09:** Retention periods must be stored in the Data Catalog (G8) as human-readable documentation alongside the schema definition. Catalog UI must surface the retention period and last erasure run date for each personal data table.

### Security & Compliance Module (G9 — M11)
This is the primary module for compliance implementation. The following APIs must be designed:

| Endpoint | Method | Checklist | Purpose |
|---|---|---|---|
| `/compliance/subject/{id}/data` | GET | C05 | Subject access request — returns all personal data records |
| `/compliance/subject/{id}` | PATCH | C05 | Rectification — correct inaccurate personal data fields |
| `/compliance/subject/{id}` | DELETE | C06 | Erasure — cascade delete/anonymise across all tables |
| `/compliance/subject/{id}/restrict` | POST | C05 | Restriction — flag subject records as restricted |
| `/compliance/subject/{id}/object` | POST | C05 | Objection — exclude subject from pipeline processing |
| `/compliance/subject/{id}/export` | GET | C07 | Portability — export personal data as JSON/CSV |
| `/compliance/consent` | POST/PATCH | C04 | Record consent; update consent version or revocation |
| `/compliance/breach` | POST | C08 | Record breach event with timestamp; trigger notification workflow |

**RBAC requirements (C10):** Default policy must be deny-all. Role definitions must specify which columns are accessible per role. Column masking must be applied server-side at query execution — the BI layer must never receive unmasked PII unless the requesting user holds the appropriate role.

**Audit log requirements (C08, C10):** Every user action involving personal data must generate an audit event: user_id, action_type, table_affected, record_count, timestamp, IP address. Audit records must be immutable (append-only log). Breach detection: anomaly in access pattern (e.g., bulk SELECT on a personal data table outside normal hours) triggers `breach_event` record automatically.

### Platform-Wide (M3 architecture through M11)
- **C10 (Privacy by Design):** M3 architecture document (the most critical document in the project) must include a dedicated compliance architecture section confirming: TLS enforcement across all inter-module connections; deny-by-default RBAC; column masking as a first-class feature of the query path (not an optional decorator); no plain-text transmission of personal data between modules.

---

## 8. VERBİS Registration Support (KVKK-Specific — M12 Documentation)

Pilot organisations subject to KVKK may be required to maintain VERBİS registrations covering their SUBOP-processed data. The M12 documentation package must include:

- **Processing activity register template:** For each pipeline, a pre-filled template covering VERBİS required fields: controller identity, data processor identity (SUBOP), processing purpose, data subject categories, personal data categories, planned retention period, recipients of transferred data, cross-border transfer details.
- **Data categories reference list:** Standard KVKK data category taxonomy mapped to SUBOP column-type classifications.

This documentation reduces the pilot organisation's VERBİS compliance burden and strengthens SUBOP's value proposition for Turkish enterprise customers.

---

## 9. Key Sources

- KVKK Official Text (Turkish): https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5
- KVKK Kurumu (Personal Data Protection Authority): https://www.kvkk.gov.tr/
- VERBİS Registry Information: https://verbis.kvkk.gov.tr/
- KVKK Breach Notification Regulation (Official Gazette 2019): https://www.kvkk.gov.tr/Icerik/6784/Kisisel-Veri-Ihlali-Bildirimi
- GDPR Full Text (EUR-Lex): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679
- European Data Protection Board (EDPB) Guidelines: https://edpb.europa.eu/our-work-tools/general-guidance/guidelines-recommendations-best-practices_en
- GDPR Art. 35 DPIA Guidelines (WP29/EDPB): https://ec.europa.eu/newsroom/article29/items/611236
- GDPR Art. 25 Privacy by Design Guidelines (EDPB): https://edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201904_dataprotection_by_design_and_by_default_v2.0_en.pdf
- IAPP KVKK vs GDPR comparison: https://iapp.org/news/a/comparing-turkish-kvkk-and-the-gdpr/
- Linklaters KVKK Overview: https://www.linklaters.com/en/insights/publications/2016/june/personal-data-protection-law-in-turkey
