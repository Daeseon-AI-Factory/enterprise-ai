# Equipment Preventive Maintenance Guide

**Document ID:** PM-MAN-003
**Revision:** 2.1
**Effective Date:** 2026-01-15
**Department:** Facilities & Equipment Engineering

---

## 1. Purpose

This guide defines preventive maintenance (PM) schedules and procedures for all SMT and assembly line equipment. Adherence to this guide reduces unplanned downtime and maintains equipment OEE above 85%.

---

## 2. Equipment Inventory

| Equipment ID | Name | Line | Type | Criticality |
|-------------|------|------|------|-------------|
| EQ-SMT-001 | Solder Paste Printer | LINE-A | SMT | Critical |
| EQ-SMT-002 | Pick & Place Machine | LINE-A | SMT | Critical |
| EQ-SMT-003 | Reflow Oven | LINE-A | SMT | Critical |
| EQ-AOI-001 | AOI Inspector | LINE-A | Inspection | High |
| EQ-ASM-001 | Screw Driver Station | LINE-B | Assembly | Medium |
| EQ-PKG-001 | Packaging Wrapper | LINE-C | Packaging | Low |

---

## 3. Preventive Maintenance Schedule

### 3.1 Daily Checks (Operator Responsibility)

- Visual inspection of all conveyor belts and feeders
- Nozzle condition check on Pick and Place machines
- Solder paste viscosity verification (acceptable range: 180-220 Pa.s)
- Air pressure gauge reading (must be 0.45-0.55 MPa)
- Log all readings in the Equipment Daily Check Sheet (FM-PM-001)

### 3.2 Weekly Maintenance

| Task | Equipment | Duration | Responsible |
|------|-----------|----------|-------------|
| Nozzle cleaning and replacement | EQ-SMT-002 | 45 min | Maintenance Tech |
| Conveyor belt tension adjustment | All lines | 30 min | Maintenance Tech |
| AOI camera lens cleaning | EQ-AOI-001 | 20 min | Quality Tech |
| Solder paste refrigerator calibration | Storage | 15 min | Material Handler |

### 3.3 Monthly Maintenance

- Full calibration of Pick and Place machine placement accuracy (target: +/- 0.05mm)
- Reflow oven temperature profile verification (9-zone profile must match specification)
- Replace air filters on all SMT equipment
- Lubricate all linear motion guides
- Inspect and clean flux traps in reflow oven

### 3.4 Quarterly Maintenance

- Full AOI system calibration with certified calibration board
- Replace reflow oven heating elements if resistance exceeds 15% of nominal
- Complete conveyor chain replacement assessment
- Update equipment firmware if new versions available

---

## 4. Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| OEE (Overall Equipment Effectiveness) | > 85% | Monthly |
| MTBF (Mean Time Between Failures) | > 720 hours | Rolling 6-month |
| MTTR (Mean Time To Repair) | < 2 hours | Per incident |
| Planned vs Unplanned Downtime Ratio | > 4:1 | Monthly |
| PM Completion Rate | > 95% | Monthly |

---

## 5. Spare Parts Management

### Critical Spares (must maintain minimum stock)

| Part | Equipment | Min Stock | Lead Time |
|------|-----------|-----------|-----------|
| SMT Nozzles (Type N08, N12, N24) | EQ-SMT-002 | 10 each | 2 weeks |
| Solder Paste Squeegee Blades | EQ-SMT-001 | 5 sets | 1 week |
| Reflow Oven Heating Elements | EQ-SMT-003 | 3 units | 4 weeks |
| AOI LED Light Sources | EQ-AOI-001 | 2 units | 3 weeks |
| Conveyor Belts (Line A spec) | LINE-A | 2 rolls | 2 weeks |

All spare parts usage must be logged in the Spare Parts Tracking System (SPTS) within 24 hours of use.

---

## 6. Downtime Logging

All equipment downtime events must be recorded using the Downtime Event Form (FM-PM-003):

1. Equipment ID and name
2. Start time and end time of downtime
3. Category: Planned PM / Unplanned Breakdown / Setup Change / Material Wait
4. Root cause description
5. Corrective action taken
6. Parts replaced (if any)
7. Technician name and sign-off

Downtime data is reviewed weekly by the Equipment Engineering team and monthly by Plant Management.

---

## 7. Emergency Breakdown Procedure

1. Operator presses emergency stop and notifies shift supervisor
2. Supervisor creates urgent maintenance ticket (priority P1)
3. Maintenance responds within 15 minutes during production hours
4. If repair exceeds 2 hours, escalate to Equipment Engineering Manager
5. After repair, run 3 test units before resuming production
6. Complete Root Cause Analysis (RCA) within 48 hours for any unplanned downtime exceeding 1 hour

---

*This document is controlled. Printed copies are for reference only.*
