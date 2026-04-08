# Warehouse Operations Manual — Ansan Distribution Center

**Document ID:** WH-OPS-003  
**Revision:** 2.1  
**Effective Date:** 2025-08-15  
**Classification:** Internal Use Only  
**Prepared by:** Logistics Engineering Group  
**Approved by:** M. Jung, Warehouse Operations Manager  

---

## 1. Facility Overview

The Ansan Distribution Center (ADC) operates a 12,000 square meter climate-controlled warehouse serving Plant Ansan SMT production lines and three regional customers. The facility runs two shifts (06:00-14:00, 14:00-22:00) Monday through Saturday. Peak throughput capacity is 4,200 SKUs per day across inbound receiving, storage, and outbound shipping.

## 2. Receiving Procedures

### 2.1 Inbound Dock Operations

1. All inbound trucks must check in at the security gate and present a valid Purchase Order (PO) number or Advanced Shipping Notice (ASN).
2. Dock supervisor assigns one of four receiving bays (R1 through R4) based on load type:
   - R1/R2: Raw materials and electronic components (ESD-protected zone)
   - R3: Packaging materials and consumables
   - R4: Oversized or hazardous goods (flammable solvents, cleaning agents)
3. Upon unloading, the receiving clerk scans each pallet barcode against the ASN in the WMS (transaction code `WH-RCV-100`).
4. Quantity discrepancies exceeding +/- 2% trigger a hold status. The clerk issues a Receiving Discrepancy Report (form WH-RDR-005) and notifies the procurement team within 2 hours.

### 2.2 Inbound Quality Sampling

- Electronic components (IC reels, passive reels): 100% label verification plus AQL 1.0 sampling for moisture sensitivity level (MSL) compliance.
- Packaging materials: visual inspection only, 5% random sampling per lot.
- All received goods must clear inbound QC within 4 hours before transfer to storage zones.

## 3. Storage Zone Layout

The warehouse is divided into three primary storage zones optimized by inventory velocity analysis conducted quarterly.

| Zone | Classification | Velocity | Location | Storage Type | Capacity |
|------|---------------|----------|----------|--------------|----------|
| A-Zone | High Velocity | Top 15% of SKUs by daily picks | Aisles A01-A08, ground level | Flow racking, carton live storage | 1,800 bin locations |
| B-Zone | Medium Velocity | Next 35% of SKUs | Aisles B01-B12, ground and level 2 | Standard selective pallet racking | 3,200 pallet positions |
| C-Zone | Bulk / Low Velocity | Bottom 50% of SKUs | Aisles C01-C10, all levels | Deep-lane push-back racking, 4-deep | 2,400 pallet positions |

### 3.1 Zone Assignment Rules

- New SKUs default to B-Zone for the first 30 days. After 30 days, the WMS recalculates velocity and reassigns the SKU automatically.
- ESD-sensitive components must be stored in A-Zone or B-Zone only (humidity-controlled aisles with RH maintained between 30% and 50%).
- MSL-3 and higher components require dry cabinet storage (below 10% RH). Dry cabinets are located in A-Zone aisle A07.
- FIFO is enforced system-wide. The WMS directs picks to the oldest lot based on goods receipt date.

## 4. Picking Strategies

### 4.1 Wave Picking (Standard Mode)

Used for routine production kit orders and customer shipments.

1. The WMS generates pick waves every 2 hours aligned to production schedules (wave triggers at 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00).
2. Each wave groups orders by destination zone to minimize travel distance.
3. Pickers use RF handheld scanners (Zebra MC9300) and follow the WMS-directed pick path.
4. Target pick rate: 45 lines per picker per hour for A-Zone, 30 lines per hour for B-Zone, 20 lines per hour for C-Zone.

### 4.2 Zone Picking (High-Volume Mode)

Activated when order volume exceeds 600 lines per wave or during end-of-month surge periods.

1. Each picker is assigned to a single zone. Partial orders are consolidated at the packing station.
2. Zone picking reduces congestion in A-Zone aisles and improves throughput by approximately 25% over wave picking during peak periods.
3. Consolidation errors must remain below 0.1%. The packing station operator verifies each order against the pick ticket using weight-check confirmation.

### 4.3 Emergency / Hot Picks

For urgent production line-down situations only, authorized by the production control manager.

1. Hot picks bypass the wave queue and are dispatched immediately to a dedicated picker.
2. Target fulfillment time: 15 minutes from request to delivery at production line staging area.
3. All hot picks are logged in the WMS under exception code `HP-URGENT` for monthly review.

## 5. Cycle Counting Schedule

Physical inventory counts are performed on a rolling cycle basis. No annual full-count shutdown.

| Zone | Count Frequency | SKUs per Count | Tolerance |
|------|----------------|----------------|-----------|
| A-Zone | Weekly (every Monday) | 100% of A-Zone SKUs per month | +/- 0.5% by value |
| B-Zone | Bi-weekly | 100% of B-Zone SKUs per quarter | +/- 1.0% by value |
| C-Zone | Monthly | 100% of C-Zone SKUs per half-year | +/- 2.0% by value |

- Discrepancies exceeding tolerance require a recount within 24 hours and a root cause investigation logged in form WH-CYC-012.
- Target inventory accuracy: 99.5% across all zones. Current trailing 12-month average: 99.3%.

## 6. Safety Protocols

1. All personnel must complete warehouse safety orientation (course WH-SAF-101) before unaccompanied access.
2. Maximum forklift speed: 8 km/h in aisles, 15 km/h in open transit lanes.
3. ESD wrist straps are mandatory in A-Zone and B-Zone aisles handling electronic components. Strap resistance must be verified at the entrance checkpoint (acceptable range: 1 to 10 megaohms).
4. Emergency exits are located at positions E1 (north dock), E2 (south wall), E3 (east office corridor), and E4 (west loading area). Evacuation drills are conducted quarterly.
5. Lithium battery storage: isolated in C-Zone aisle C10 with Class D fire extinguishers within 5 meters. Maximum storage quantity: 500 kg per bay per fire code regulation FCC-2024-LB.
6. Near-miss incidents must be reported within the same shift using the digital form on the warehouse safety kiosk (terminal WH-K01 or WH-K02).

---

*End of Document WH-OPS-003 Rev 2.1*
