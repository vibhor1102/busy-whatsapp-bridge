# Tran3, Tran4, Tran5, Tran6 Table Analysis

**Analysis Date:** 2026-02-23  
**Database:** `C:\Users\Vibhor\Desktop\COMP0012\db12025.bds`  
**Analyst:** Database Analysis Script

---

## Executive Summary

These four tables are **supplementary transaction tables** that extend the core transaction functionality (Tran1/Tran2) with specialized tracking features:

| Table | Columns | Rows | Purpose | Status |
|-------|---------|------|---------|--------|
| **Tran3** | 33 | 15,707 | Bill-wise/Reference-wise transaction details | **ACTIVE** |
| **Tran4** | 8 | 2,816 | Monthly/Period-wise balance summary | **ACTIVE** |
| **Tran5** | 16 | 0 | Additional tracking details | **NOT USED** |
| **Tran6** | 7 | 0 | Stock type tracking | **NOT USED** |

---

## 1. Tran3 - Bill-wise/Reference-wise Details

### 1.1 Purpose
Tran3 stores **bill-wise or reference-wise tracking information** for transactions. This is crucial for:
- Tracking individual bills/invoices against payments/receipts
- Managing outstanding balances per bill
- Supporting "Against Reference" accounting methodology

### 1.2 Schema (33 Columns)

| Column | Type | Description |
|--------|------|-------------|
| `RefCode` | Integer | Unique reference identifier (7,676 unique values) |
| `RecType` | Integer | Record type: 1=New Ref, 4/5=Adjustments |
| `Method` | Integer | Bill tracking method (1,2,3) |
| `VchCode` | Integer | Links to **Tran1** (10,804 unique vouchers) |
| `VchType` | Integer | Voucher type code |
| `MasterCode1` | Integer | Party/Ledger code from Master1 |
| `MasterCode2` | Integer | Additional master reference |
| `RefGrp` | Integer | Reference group code |
| `SrNo` | Integer | Serial number within voucher |
| `Date` | DateTime | Transaction date |
| `DueDate` | DateTime | Due date for payment |
| `No` | String(25) | Bill/Invoice number |
| `Status` | Integer | Bill status flag |
| `Type` | Integer | Type classification |
| `BrokerCode` | Integer | Broker reference |
| `Value1` | Float | Bill amount (primary) |
| `Value2` | Float | Additional amount field |
| `Value3` | Float | Additional amount field |
| `Balance1` | Float | Outstanding balance |
| `Balance2` | Float | Secondary balance |
| `Balance3` | Float | Tertiary balance |
| `ItemSrNo` | Integer | Links to item in Tran2 |
| `MfgDate` | DateTime | Manufacturing date (unused) |
| `TranType` | Integer | Transaction type classification |
| `CM1` | Integer | Custom master field 1 |
| `CM2` | Integer | Custom master field 2 |
| `CM3` | Integer | Custom master field 3 |
| `ApprovalStatus` | Integer | Approval workflow status |
| `NewRefAmount` | Float | Amount for new reference creation |
| `Narration` | String(255) | Description/narration |
| `BranchCode` | Integer | Branch identifier |
| `NewRefVchType` | Integer | Voucher type for new reference |
| `NewRefVchCode` | Integer | Voucher code for new reference |

### 1.3 Data Distribution

**RecType Breakdown:**
- **RecType 1**: 15,528 rows (98.9%) - **New References** (original bills)
- **RecType 5**: 174 rows (1.1%) - **Adjustments** (allocations/adjustments)
- **RecType 4**: 5 rows (0.03%) - **Other adjustments**

**Method Breakdown:**
- **Method 2**: 7,872 rows (50.1%)
- **Method 1**: 7,675 rows (48.9%)
- **Method 3**: 160 rows (1.0%)

*Note: Method likely indicates the bill tracking mode (New Ref, Against Ref, On Account)*

**VchType Distribution (Top 5):**
- **VchType 14**: 5,579 rows (35.5%) - **Sales Invoices**
- **VchType 9**: 4,985 rows (31.7%) - **Purchase Vouchers**
- **VchType 19**: 1,791 rows (11.4%) - **Receipt Vouchers**
- **VchType 2**: 1,695 rows (10.8%) - **Payment Vouchers**
- **VchType 1**: 659 rows (4.2%) - **Contra/Journal**

### 1.4 Sample Data

**New Reference (RecType=1):**
```
RefCode=10283, VchCode=14114, Method=2
No='AHF-6338', Value1=11,496.00, Balance1=0.00
Date: 2026-01-15, DueDate: 2026-01-15
```

**Adjustment (RecType=5):**
```
RefCode=7839, VchCode=14119, Method=2
No='GN-1611/2025-26', Value1=-54,383.00 (negative = adjustment)
```

### 1.5 Link to Main Transactions

**Primary Link: Tran3.VchCode → Tran1.VchCode**
- 14,891 out of 15,707 rows (94.8%) successfully link to Tran1
- 816 rows (5.2%) are orphaned (may be deleted transactions)

**Secondary Link: Tran3.ItemSrNo → Tran2.SrNo**
- Links to specific line items when bill-wise tracking is item-level

### 1.6 Ledger Impact

**YES** - Tran3 contains essential data for ledgers:
- Outstanding bill amounts (`Value1`, `Balance1`)
- Due dates for aging analysis
- Bill numbers for reference
- Links party codes to specific bills

**Use Case:** To calculate a party's outstanding balance:
```sql
SELECT MasterCode1, SUM(Balance1) 
FROM Tran3 
WHERE Balance1 <> 0 
GROUP BY MasterCode1
```

---

## 2. Tran4 - Monthly/Period Balance Summary

### 2.1 Purpose
Tran4 stores **period-wise summary balances** for ledgers. This is used for:
- Fast period-end balance reporting
- Trial balance generation
- Financial statement preparation
- Historical balance tracking

### 2.2 Schema (8 Columns)

| Column | Type | Description |
|--------|------|-------------|
| `SrNo` | Integer | Serial number (1 or 2 per ledger) |
| `MasterCode1` | Integer | Links to **Master1** (Ledger code) - 2,367 unique |
| `MasterCode2` | Integer | Period/Category code (201 = current period?) |
| `D1` | Float | Debit/Credit amount 1 |
| `D2` | Float | Debit/Credit amount 2 |
| `D3` | Float | Debit/Credit amount 3 |
| `BranchCode` | Integer | Branch identifier (always 0) |
| `RecType` | Integer | Always 0 in current data |

### 2.3 Data Distribution

**All records:** RecType = 0

**MasterCode2 Distribution:**
- **MasterCode2 = 201**: 2,272 rows (80.7%) - **Likely "Current Period"**
- **MasterCode2 = 28542**: 544 rows (19.3%) - **Likely specific period code**

**Structure Pattern:**
Most ledgers have 2 rows in Tran4:
- Row 1: MasterCode2=201 (primary/current period)
- Row 2: MasterCode2=28542 (secondary/historical period)

### 2.4 Sample Data

```
Ledger 23759:
  Period 201: D1=38.0, D2=38.0, D3=29,925.0
  
Ledger 23762:
  Period 201: D1=90.0, D2=90.0, D3=160,470.37
  Period 28542: D1=-6.0, D2=-6.0, D3=-4,231.5 (adjustment)
```

### 2.5 Link to Main Transactions

**Primary Link: Tran4.MasterCode1 → Master1.Code**
- 100% of rows (2,816/2,816) link to Master1
- Covers 2,367 unique ledgers

**No direct link to Tran1/Tran2** - this is a summary table derived from transaction data.

### 2.6 Ledger Impact

**YES** - Tran4 is critical for ledger reporting:
- Pre-calculated period balances
- Eliminates need to sum all Tran1 entries for balance
- Stores D1, D2, D3 which likely represent:
  - D1: Opening balance
  - D2: Current period movement
  - D3: Closing balance

**Use Case:** Quick balance lookup without aggregating Tran1:
```sql
SELECT m1.Name, t4.D1, t4.D2, t4.D3
FROM Tran4 t4
JOIN Master1 m1 ON t4.MasterCode1 = m1.Code
WHERE t4.MasterCode2 = 201
```

---

## 3. Tran5 - Additional Tracking Details

### 3.1 Purpose
Tran5 would store **additional tracking information** for transactions:
- Delivery tracking numbers
- Courier details
- Additional narration
- Custom tracking fields

### 3.2 Schema (16 Columns)

| Column | Type | Description |
|--------|------|-------------|
| `VchCode` | Integer | Links to Tran1 |
| `MasterCode1` | Integer | Primary master code |
| `MasterCode2` | Integer | Secondary master code |
| `SrNo` | Integer | Serial number |
| `VchType` | Integer | Voucher type |
| `Date` | DateTime | Transaction date |
| `VchNo` | String(25) | Voucher number |
| `VchSeriesCode` | Integer | Voucher series |
| `Value1` | Float | Value field 1 |
| `Value2` | Float | Value field 2 |
| `Balance1` | Float | Balance field 1 |
| `Balance2` | Float | Balance field 2 |
| `TranType` | Integer | Transaction type |
| `ShortNar` | String(40) | Short narration |
| `TrackingNo` | String(255) | Tracking number |
| `TrackingStatus` | Integer | Tracking status |

### 3.3 Status

**Table is EMPTY (0 rows)**

This indicates:
- Tracking features are **not enabled** in this company
- OR the company doesn't use delivery tracking
- OR tracking is stored elsewhere

### 3.4 Ledger Impact

**NO** - Empty table has no current impact on ledgers.

If populated, would provide:
- Additional transaction metadata
- Tracking information for logistics
- Extended narration capabilities

---

## 4. Tran6 - Stock Type Details

### 4.1 Purpose
Tran6 would store **stock tracking by type/category**:
- Stock classification (damaged, expired, etc.)
- Multi-location stock tracking
- Batch-wise stock categorization

### 4.2 Schema (7 Columns)

| Column | Type | Description |
|--------|------|-------------|
| `SrNo` | Integer | Serial number |
| `MasterCode1` | Integer | Item/Ledger code |
| `MasterCode2` | Integer | Additional master reference |
| `StockType` | Integer | Stock type/category code |
| `D1` | Float | Quantity/Amount 1 |
| `D2` | Float | Quantity/Amount 2 |
| `D3` | Float | Quantity/Amount 3 |

### 4.3 Status

**Table is EMPTY (0 rows)**

This indicates:
- Stock type tracking is **not used** in this company
- The company doesn't classify stock by type
- OR uses a different tracking method

### 4.4 Ledger Impact

**NO** - Empty table has no current impact on ledgers.

If populated, would enable:
- Stock categorization reporting
- Type-wise inventory analysis
- Multi-dimensional stock tracking

---

## 5. Table Relationships

### 5.1 Entity Relationship Diagram

```
Master1 (Ledgers/Items)
    │
    ├──◄── Tran4 (Period balances - 2,367 ledgers)
    │
    └──◄── Tran1 (Transactions)
            │
            ├──◄── Tran3 (Bill-wise details - 94.8% linked)
            │       RefCode (bill tracking)
            │
            └──◄── Tran2 (Item details)
                    │
                    └──◄── Tran6 (Stock types - UNUSED)

Tran5 (Tracking - UNUSED)
    └──◄── Links to Tran1 (if used)
```

### 5.2 Key Relationships Summary

| From | To | Via | Cardinality | Notes |
|------|-----|-----|-------------|-------|
| Tran3 | Tran1 | VchCode | Many-to-One | 94.8% linked |
| Tran3 | Master1 | MasterCode1 | Many-to-One | Party reference |
| Tran4 | Master1 | MasterCode1 | Many-to-One | 100% linked |
| Tran5 | Tran1 | VchCode | Many-to-One | Unused table |
| Tran6 | Master1 | MasterCode1 | Many-to-One | Unused table |

### 5.3 Voucher Type Mapping

**Tran3 Distribution by Voucher Type:**

| VchType | Count | % | Likely Voucher Type |
|---------|-------|---|---------------------|
| 14 | 5,579 | 35.5% | Sales Invoice |
| 9 | 4,985 | 31.7% | Purchase |
| 19 | 1,791 | 11.4% | Receipt |
| 2 | 1,695 | 10.8% | Payment |
| 1 | 659 | 4.2% | Contra/Journal |
| 16 | 484 | 3.1% | Credit Note |
| 3 | 265 | 1.7% | Sales Return |
| 26 | 171 | 1.1% | Debit Note |
| 10 | 45 | 0.3% | Stock Journal |
| 18 | 18 | 0.1% | Purchase Order |

---

## 6. Usage Recommendations

### 6.1 For Ledger Reporting

**Essential Tables:**
1. **Tran4** - Use for fast balance lookups
2. **Tran3** - Use for bill-wise outstanding reports
3. **Tran1** - Always verify with actual transaction data

**Recommended Join:**
```sql
-- Outstanding bills by party
SELECT 
    m1.Name as Party,
    t3.No as BillNo,
    t3.Date as BillDate,
    t3.DueDate,
    t3.Value1 as BillAmount,
    t3.Balance1 as Outstanding
FROM Tran3 t3
JOIN Master1 m1 ON t3.MasterCode1 = m1.Code
WHERE t3.RecType = 1
  AND t3.Balance1 <> 0
ORDER BY m1.Name, t3.Date
```

### 6.2 For Financial Statements

**Use Tran4 for speed:**
```sql
-- Period balances
SELECT 
    m1.Name,
    m1.MasterType,
    t4.D1 as Opening,
    t4.D2 as Movement,
    t4.D3 as Closing
FROM Tran4 t4
JOIN Master1 m1 ON t4.MasterCode1 = m1.Code
WHERE t4.MasterCode2 = 201  -- Current period
```

### 6.3 Data Quality Notes

1. **Tran3 has 816 orphaned rows** (5.2%) without Tran1 links
   - May be deleted transactions
   - Consider cleanup or investigation

2. **Tran5 and Tran6 are unused**
   - Safe to ignore for current reporting
   - May be needed if company enables features

3. **Tran4 has summary data only**
   - Always verify critical calculations against Tran1
   - May have timing differences

---

## 7. Appendix: Column Value Reference

### 7.1 Tran3 RecType Values

| Value | Meaning | Count |
|-------|---------|-------|
| 1 | New Reference (Bill created) | 15,528 |
| 4 | Adjustment Type 1 | 5 |
| 5 | Adjustment Type 2 | 174 |

### 7.2 Tran3 Method Values

| Value | Meaning | Count |
|-------|---------|-------|
| 1 | Method 1 (New Ref/Against Ref) | 7,675 |
| 2 | Method 2 (On Account) | 7,872 |
| 3 | Method 3 (Other) | 160 |

### 7.3 Tran4 MasterCode2 Values

| Value | Meaning | Count |
|-------|---------|-------|
| 201 | Current Period | 2,272 |
| 28542 | Historical Period | 544 |

---

## 8. Conclusion

The four supplementary tables serve distinct purposes:

- **Tran3**: **CRITICAL** - Active bill-wise tracking (15,707 records)
- **Tran4**: **IMPORTANT** - Period balance summaries (2,816 records)  
- **Tran5**: **UNUSED** - Tracking module not enabled (0 records)
- **Tran6**: **UNUSED** - Stock types not used (0 records)

For the WhatsApp gateway project:
- **Focus on Tran3** for bill-wise invoice notifications
- **Use Tran4** for balance summary in messages
- **Ignore Tran5/6** - no data present
- **Always link through Master1** for party details

---

*Document generated by: `scripts/analyze_tran3_6.py`*  
*Analysis timestamp: 2026-02-23*
