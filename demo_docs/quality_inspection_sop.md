# Standard Operating Procedure: In-Line Quality Inspection — SMT Production

**Document ID:** QI-SOP-001  
**Revision:** 3.2  
**Effective Date:** 2025-11-01  
**Classification:** Internal Use Only  
**Prepared by:** Quality Engineering Team, Plant Ansan  
**Approved by:** K. Park, Director of Quality Assurance  

---

## 1. Purpose

This procedure defines the inspection requirements, acceptance criteria, and corrective action workflow for Surface Mount Technology (SMT) production lines at Plant Ansan (Lines S1 through S6). It applies to all solder paste printing, component placement, and reflow soldering stages. Adherence to this SOP is mandatory for all quality inspectors, line engineers, and shift supervisors.

## 2. Scope

This SOP covers:

- Pre-reflow visual and automated inspections
- Post-reflow Automated Optical Inspection (AOI) and X-ray analysis
- Final outgoing quality audit (OQA) sampling
- Defect classification, escalation, and corrective action

Product families covered: automotive ECU boards (P/N prefix AE-), consumer IoT modules (P/N prefix CI-), and industrial controller boards (P/N prefix IC-).

## 3. Referenced Standards

| Standard | Description |
|----------|-------------|
| IPC-A-610H | Acceptability of Electronic Assemblies |
| IPC-J-STD-001G | Soldering Requirements |
| IATF 16949:2016 | Automotive Quality Management (for AE- series only) |
| Internal Spec QS-200 | Plant-specific defect classification matrix |

## 4. Inspection Stages and Procedures

### 4.1 Stage 1 — Solder Paste Inspection (SPI)

Performed immediately after solder paste printing and before component placement.

1. The SPI system (Koh Young KY8030-3) automatically scans 100% of boards exiting the printer.
2. The system measures paste volume, height, area, and positional offset for each pad.
3. Acceptable thresholds:
   - Paste volume deviation: within +/- 15% of nominal
   - Paste height: 100 to 150 micrometers (for 120 um stencil)
   - Positional offset: no more than 25% of pad width
4. Any board exceeding thresholds triggers an automatic line stop and audible alarm.
5. The operator must record the reject in MES (transaction code `SPI-REJ`) and segregate the board into the red-tagged rework bin.
6. If three consecutive boards fail SPI, the printer operator must execute stencil cleaning per procedure MT-CLN-004 and notify the shift supervisor.

### 4.2 Stage 2 — Post-Placement Visual Check

Performed by a trained operator at the end of the pick-and-place section, before boards enter the reflow oven.

1. Operator performs a 5-second visual scan of each board under 3x magnification lamp.
2. Check for: missing components, tombstoned passives, rotated ICs, foreign object debris (FOD).
3. Any suspect board is flagged with a yellow sticker and set aside for engineering review.
4. This stage is a screening gate only. It does not replace AOI.

### 4.3 Stage 3 — Automated Optical Inspection (AOI)

Performed immediately after reflow soldering. This is the primary defect detection gate.

1. AOI system (Omron VT-S730) inspects 100% of boards.
2. The AOI program for each product must be validated against a golden board set (minimum 5 known-good boards) before production start.
3. Defect categories detected: solder bridges, insufficient solder, cold joints, missing components, polarity reversal, lifted leads, billboarding.
4. **Acceptance criteria:**
   - Overall solder defect rate (DPMO basis): must not exceed **2.0%** per lot
   - Critical defect rate (solder bridges on fine-pitch QFP/BGA): must not exceed **0.5%**
   - Cosmetic-only defects (minor solder excess, non-functional): tracked but not gated
5. AOI false call rate target: below 3%. If false calls exceed 5% over a shift, the AOI engineer must recalibrate the inspection program.
6. All AOI rejects are placed in the orange-tagged review station for manual verification within 30 minutes.

### 4.4 Stage 4 — X-Ray Inspection

Required for all BGA, QFN, and LGA packages where solder joints are hidden beneath the component body.

1. X-ray system (Nikon XT V 160) is used on a sampling basis: minimum 1 board per panel, or 5% of lot quantity, whichever is greater.
2. For automotive-grade boards (AE- prefix): 100% X-ray inspection is mandatory per IATF 16949 customer-specific requirements.
3. Evaluation criteria per IPC-7095D:
   - Void area in BGA solder balls: must not exceed 25% of ball cross-section
   - Head-in-pillow defects: zero tolerance
   - Bridging between adjacent BGA balls: zero tolerance
4. X-ray images are archived in the QMS database with board serial number traceability for a minimum of 10 years (automotive) or 5 years (all others).

### 4.5 Stage 5 — Outgoing Quality Audit (OQA)

Performed on finished-goods before shipment.

1. Sampling plan per ANSI/ASQ Z1.4 Level II, normal inspection.
2. AQL: 0.65% for critical defects, 1.5% for major defects, 4.0% for minor defects.
3. OQA inspector must complete checklist form QI-CHK-050 and attach to the lot traveler.
4. Any OQA lot rejection triggers immediate containment per Section 5.

## 5. Escalation and Corrective Action

### 5.1 Defect Rate Escalation Matrix

| Condition | Action | Response Time | Owner |
|-----------|--------|---------------|-------|
| Lot solder defect rate 2.0% to 3.0% | Issue Quality Alert (QA-ALERT) to line supervisor | 15 minutes | Shift QC Lead |
| Lot solder defect rate 3.0% to 5.0% | Stop the line. Convene rapid response team. | Immediate | Production Manager |
| Lot solder defect rate above 5.0% | Full line shutdown. Quarantine all WIP from the shift. Notify Plant QA Director. | Immediate | Plant QA Director |
| Any single critical defect on AE- product | Stop shipment. Issue 8D report (form QI-8D-001) to customer within 24 hours. | 24 hours | Quality Engineering |

### 5.2 Corrective Action Process

1. Upon defect rate exceedance, the responsible engineer opens a Corrective Action Request (CAR) in the QMS system using form QI-CAR-010.
2. Root cause analysis must use at minimum the 5-Why method. Fishbone diagrams are required for defect rates exceeding 5%.
3. Interim containment action must be implemented within 4 hours.
4. Permanent corrective action must be verified effective within 10 business days.
5. The CAR is closed only after the QA Manager confirms that the defect rate has returned below threshold for 3 consecutive production lots.

## 6. Records and Retention

- SPI, AOI, and X-ray inspection data: retained in MES database for minimum 5 years (10 years for automotive).
- CAR records: retained for 7 years.
- OQA checklists: retained for 5 years.
- All records are subject to audit by the Quality Management Representative during scheduled internal audits per ISO 9001 clause 9.2.

## 7. Revision History

| Rev | Date | Description | Author |
|-----|------|-------------|--------|
| 1.0 | 2023-03-15 | Initial release | J. Lee |
| 2.0 | 2024-01-10 | Added X-ray mandatory requirement for AE- products | S. Kim |
| 3.0 | 2024-09-01 | Updated AOI false call threshold from 8% to 5% | H. Cho |
| 3.1 | 2025-04-20 | Added OQA sampling plan reference | K. Park |
| 3.2 | 2025-11-01 | Revised solder defect rate threshold from 3% to 2% | K. Park |

---

*End of Document QI-SOP-001 Rev 3.2*
