# Transaction Tables Analysis: Tran7 - Tran12

**Database:** `C:\Users\Vibhor\Desktop\COMP0012\db12025.bds`  
**Analysis Date:** 2026-02-23  
**Method:** Python 3.14 (32-bit) with pyodbc

---

## Executive Summary

| Table | Columns | Rows | Status | Purpose |
|-------|---------|------|--------|---------|
| **Tran7** | 1 | 2,059 | **POPULATED** | Active Master Codes Registry |
| **Tran8** | 19 | 0 | EMPTY | CST/Form Receipt Tracking |
| **Tran9** | 9 | 0 | EMPTY | Form Detail Records |
| **Tran10** | 35 | 349 | **POPULATED** | **GST/HSN Codes & Party GST Numbers** |
| **Tran11** | 31 | 0 | EMPTY | Transaction References |
| **Tran12** | 4 | 3,261 | **POPULATED** | Print Audit Log |

**Critical Tables:** Tran10 (GST compliance data)  
**Useful Tables:** Tran7 (master reference), Tran12 (audit trail)  
**Empty/Unused:** Tran8, Tran9, Tran11

---

## Detailed Analysis

### Tran7 - Active Master Codes Registry

**Structure:**
- **Columns:** 1 (MasterCode: Integer)
- **Rows:** 2,059
- **Primary Key:** MasterCode

**Purpose:**  
This is a simple registry table containing all Master Codes that are currently active or in use within the system. Each MasterCode appears exactly once (no duplicates), suggesting this is used as a validation or lookup table to quickly check if a master exists.

**Data Characteristics:**
- Contains 2,059 unique MasterCode values
- All MasterCodes are unique (1 occurrence each)
- Sample codes: 33799, 33874, 29216, 28194, 33875
- Links to: `Master.Code` table

**Use Case:**  
Used for validating master codes during transactions. When creating vouchers or processing data, the system can quickly check if a MasterCode exists in Tran7 before proceeding.

**Criticality:** Medium - Useful for data validation but not transaction-critical.

---

### Tran8 - CST/Form Receipt Tracking (Empty)

**Structure:**
- **Columns:** 19
- **Rows:** 0 (EMPTY)
- **Key Columns:**
  - `VchCode` - Voucher code
  - `VchType` - Voucher type
  - `Date` - Transaction date
  - `FormRecDate` - Form receipt date
  - `FormNo` - Form number
  - `PartyCode` - Party master code
  - `FormCode` - Form type code
  - `CreatedBy`, `CreationTime` - Audit fields
  - `AuthorisedBy`, `AuthorisationTime` - Authorization tracking

**Purpose:**  
Designed to track CST (Central Sales Tax) forms and declaration forms received from parties. This would store records of Form C, Form F, or other statutory forms submitted by customers/suppliers.

**Current Status:**  
Completely empty (0 rows). CST forms tracking is not currently in use or has been migrated to a different system.

**Criticality:** Low - Empty and likely deprecated in GST era.

---

### Tran9 - Form Detail Records (Empty)

**Structure:**
- **Columns:** 9
- **Rows:** 0 (EMPTY)
- **Key Columns:**
  - `VchCode` - Voucher reference
  - `PartyCode` - Party master code
  - `FormCode` - Form type
  - `FormNo` - Form number
  - `BillCode` - Related bill reference
  - `Amount` - Amount covered by form

**Purpose:**  
Stores line-item details of forms received. Works in conjunction with Tran8 to track which specific bills/vouchers are covered by each form received from parties.

**Current Status:**  
Completely empty (0 rows). Not in use.

**Criticality:** Low - Empty and likely deprecated.

---

### Tran10 - GST/HSN Codes & Party GST Numbers **(CRITICAL)**

**Structure:**
- **Columns:** 35 (flexible storage structure)
- **Rows:** 349
- **Key Columns:**
  - `RecType` - Record type discriminator
  - `VchType` - Voucher type
  - `I1-I4` - Integer fields
  - `D1-D10` - Decimal/numeric fields
  - `C1-C10` - Character/string fields
  - `B1-B3` - Boolean flags
  - `M1` - Memo/long text

**Purpose:**  
This is a **critical table** containing GST compliance data. It stores:
1. **HSN/SAC Codes** (RecType = 32) - Product/service classification codes
2. **Party GST Numbers** (RecType = 33) - GSTIN of parties

**Data Distribution:**
| RecType | Count | Purpose |
|---------|-------|---------|
| 33 | 299 | Party GST Numbers (85.7%) |
| 32 | 49 | HSN/SAC Codes (14.0%) |
| 26 | 1 | Unknown type (0.3%) |

**Sample HSN Codes (RecType 32):**
| Code | Description |
|------|-------------|
| 57024210 | CARPET |
| 5703 | DOORMATS |
| 570330 | DOORMATS |
| 5811 | QUILTED BED COVER |
| 5904 | YOGA MATS |
| 59049090 | DISH DRY MATS |
| 6207 | BATH ROB |
| 6301 | BLANKETS |

**Sample Party GST Numbers (RecType 33):**
| Party Name | GSTIN |
|------------|-------|
| A D LOGISTICS | 07ACAFA9584F1Z9 |
| A T C | (empty) |
| A.D.S TRANSPORT | 06AHSPC5495N1ZL |

**Use Case:**  
- Essential for GST invoice generation
- Required for GSTR-1 filing
- Links HSN codes to items
- Links GSTIN to parties for invoice printing
- MasterCode1 in RecType 32 records points to the item master (e.g., 1054)

**Criticality:** **HIGH** - Required for GST compliance and invoice generation.

---

### Tran11 - Transaction References (Empty)

**Structure:**
- **Columns:** 31
- **Rows:** 0 (EMPTY)
- **Key Columns:**
  - `RecType` - Record type
  - `TranType` - Transaction type
  - `VchCode` - Voucher reference
  - `MasterCode1`, `MasterCode2` - Master references
  - `VchNo` - Voucher number
  - `ShortNar` - Short narration
  - `Date1-Date5` - Multiple date fields
  - `C1`, `C2` - Character fields
  - `M1`, `M2` - Memo fields

**Purpose:**  
Designed to store additional transaction-level references, supporting documents, or extended narration. The multiple date and memo fields suggest this was meant for complex reference tracking.

**Current Status:**  
Completely empty (0 rows). Not in use.

**Criticality:** Low - Empty and not currently utilized.

---

### Tran12 - Print Audit Log

**Structure:**
- **Columns:** 4
- **Rows:** 3,261
- **Columns:**
  - `VchCode` - Voucher that was printed
  - `Date` - When it was printed
  - `UserName` - Who printed it
  - `NoOfCopies` - How many copies

**Purpose:**  
Audit trail tracking every voucher print operation. Records who printed what document, when, and how many copies.

**Print Activity by User:**
| User | Prints | Percentage |
|------|--------|------------|
| Nitin | 2,493 | 76.4% |
| TANYA | 476 | 14.6% |
| Anuj | 136 | 4.2% |
| AMIT | 97 | 3.0% |
| Rohit | 28 | 0.9% |
| Sourav | 18 | 0.6% |
| ARJUN | 13 | 0.4% |

**Date Range:**
- **Earliest:** 2025-04-14 12:16:03
- **Latest:** 2026-02-18 13:15:11
- **Activity Period:** ~10 months

**Sample Records:**
```
VchCode  | Date                | User  | Copies
---------|---------------------|-------|-------
10530    | 2025-11-22 11:38:44 | TANYA | 2
10532    | 2025-11-22 11:42:03 | TANYA | 1
10544    | 2025-11-22 14:17:56 | Nitin | 1
```

**Use Case:**
- Track document printing for audit purposes
- Monitor user activity
- Verify invoice/document distribution
- Re-print tracking

**Criticality:** Medium - Important for audit trails but not transaction-critical.

---

## Key Findings

### 1. Data Distribution
- **3 populated tables** out of 6 (50%)
- **Total rows:** 5,669 (2,059 + 349 + 3,261)
- **Critical transaction data:** 349 rows (Tran10)

### 2. Empty Tables Analysis
- **Tran8, Tran9:** Related to CST/Form tracking (pre-GST era)
- **Tran11:** Advanced reference tracking (unused feature)
- These tables may have been populated in earlier accounting periods or are features not currently utilized

### 3. GST Compliance
- **Tran10 is essential** for GST operations
- Contains 299 party GST numbers and 49 HSN codes
- Links to Master table via MasterCode1
- Required for invoice generation and GSTR filing

### 4. Master Registry
- **Tran7** contains 2,059 active master codes
- Provides quick validation reference
- May be used to optimize queries against the Master table

### 5. Audit Trail
- **Tran12** provides comprehensive print tracking
- 7 different users have printed vouchers
- 10 months of activity tracked
- Useful for compliance and monitoring

---

## Recommendations

### For WhatsApp Integration
1. **Tran10** should be referenced to:
   - Get party GSTIN for invoice messages
   - Validate HSN codes for product queries
   - Link voucher codes to master data

2. **Tran12** could be used to:
   - Track which invoices have been printed (and thus likely sent)
   - Identify recently printed vouchers for follow-up

3. **Tran7** can help validate:
   - Party codes before querying
   - Item codes before processing

### Data Maintenance
- Empty tables (Tran8, Tran9, Tran11) can be archived if not needed
- Tran10 should be regularly backed up (GST-critical data)
- Tran12 provides good audit data but can be purged periodically

### Query Optimization
When querying transaction data:
```sql
-- Use Tran7 to validate master codes quickly
SELECT m.* FROM Master m 
INNER JOIN Tran7 t ON m.Code = t.MasterCode
WHERE m.Code = ?

-- Get GST details from Tran10
SELECT C1 as GSTIN, C2 as PartyName 
FROM Tran10 
WHERE RecType = 33 AND MasterCode1 = ?

-- Check if voucher was printed
SELECT * FROM Tran12 WHERE VchCode = ?
```

---

## Appendix: Table Relationships

```
Tran7.MasterCode → Master.Code (validation reference)
Tran10.MasterCode1 → Master.Code (GST/HSN linkage)
Tran12.VchCode → Tran1.VchCode (print tracking)
```

## Data Files

- Analysis JSON: `tran7_12_analysis.json`
- Full database analysis: `database_analysis.json`
- This document: `docs/table_analysis_tran7_12.md`
