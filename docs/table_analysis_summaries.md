# DailySum and CheckList Table Analysis

**Analysis Date:** 2026-02-23  
**Database:** COMP0012\db12025.bds  
**Tables Analyzed:** DailySum, CheckList

---

## Executive Summary

Both tables contain **pre-calculated summary data** that is extremely useful for ledger queries:

- **DailySum**: Contains daily debit/credit summaries per master account
- **CheckList**: Contains audit trail/check log records with amounts

These tables eliminate the need to aggregate transactions in real-time for balance calculations.

---

## DailySum Table Analysis

### Basic Statistics
- **Total Rows:** 20,275
- **Unique Masters:** 2,984 (MasterCode1)
- **Secondary Masters:** 1 unique MasterCode2 (non-zero)
- **Date Range:** April 1, 2025 to March 31, 2026 (full fiscal year)

### Schema
| Column | Type | Description |
|--------|------|-------------|
| MasterCode1 | Integer | Primary master account code |
| MasterCode2 | Integer | Secondary master (rarely used) |
| MasterType | Integer | Type 2 (Ledgers) or Type 6 (other) |
| Date | DateTime | Summary date |
| Dr1 | Float | Debit amount (primary) |
| Dr2 | Float | Debit amount (secondary) |
| Dr3 | Float | Debit amount (tertiary) |
| Cr1 | Float | Credit amount (primary) |
| Cr2 | Float | Credit amount (secondary) |
| Cr3 | Float | Credit amount (tertiary) |
| D1-D4 | Float | Additional data fields (all 0 in sample) |

### Key Findings

#### 1. Daily Summaries Per Master
**YES - This table contains daily summaries.**

- 1,766 masters have entries for multiple dates
- Master 27232 has 335 unique date entries (almost every day of the year)
- Master 1 (likely Cash/Bank) has 322 date entries
- Pattern shows one row per master per day where activity occurred

#### 2. Balance Information
**YES - Contains running balance data.**

- **Dr1/Cr1** appear to be the primary debit/credit fields
- **Dr2/Cr2** and **Dr3/Cr3** support multi-currency or multi-location accounting
- Example: Master 27232 on 2025-11-14 had Dr1=215,668.92 and Cr1=1,100,785.00

#### 3. Master Type Distribution
| MasterType | Count | Description |
|------------|-------|-------------|
| Type 2 | 16,439 | Ledger accounts (LedMst) |
| Type 6 | 3,836 | Other masters (likely items/groups) |

### Relationship to Transactions

**Direct pre-aggregation of Tran1-Tran12 tables:**

DailySum aggregates the transaction detail tables (Tran1 through Tran12) by:
- MasterCode1 (account)
- Date (voucher date)

This allows instant balance calculation without scanning transaction tables.

### Sample Data
```
Date: 2025-11-13, Master: 13965, Dr1: 145,101.00, Cr1: 0.00
Date: 2025-11-14, Master: 27232, Dr1: 215,668.92, Cr1: 1,100,785.00
Date: 2025-04-01, Master: 1, Dr1: 89,693.00, Cr1: 1,320.00
```

---

## CheckList Table Analysis

### Basic Statistics
- **Total Rows:** 29,892
- **Date Range:** April 1, 2025 to February 18, 2026
- **Users:** 10+ distinct users (Nitin, TANYA, AMIT, etc.)

### Schema
| Column | Type | Description |
|--------|------|-------------|
| Type | Integer | Record type (1=Master, 2=Voucher) |
| Code | Integer | Reference code (MasterCode or VchCode) |
| Action | Integer | 1=Create, 2=Modify |
| ActionTime | DateTime | When action occurred |
| UserName | String | User who performed action |
| D1 | Float | Usually count or quantity |
| D2 | Float | Usually count or quantity |
| D3 | Float | **Amount field** (most important) |
| D4 | Float | Always 0 (unused) |
| D5 | Float | Always 0 (unused) |
| Notes | Memo | Notes/comments |
| ComputerName | String | Workstation name |

### Key Findings

#### 1. What is being checked?
**Audit trail for voucher and master record modifications:**

- **Type 2** (84.5%): Voucher-related checks/audits
  - 25,260 rows tracking voucher modifications
  - D3 field contains voucher amounts (up to 3,000,000.00)
  
- **Type 1** (15.5%): Master record checks
  - 4,632 rows tracking master modifications
  - D1/D2 fields often non-zero (possibly item counts)

#### 2. Action Types
| Action | Count | Description |
|--------|-------|-------------|
| Action 1 | 18,087 | Creation/Addition |
| Action 2 | 11,805 | Modification/Update |

#### 3. D Field Analysis
| Field | Non-Zero % | Max Value | Purpose |
|-------|------------|-----------|---------|
| D1 | 55% | 24,524,676 | Count/Quantity |
| D2 | 54% | 26,982 | Count/Quantity |
| D3 | 85% | 3,000,000 | **Amount** |
| D4 | 0% | 0 | Unused |
| D5 | 0% | 0 | Unused |

### Sample Data

**Type 2 (Voucher Audit):**
```
Code=15646, Action=1 (Create), User=TANYA, Time=2026-02-18 13:52:34
  D1=0, D2=0, D3=200,000.00 ← Voucher amount
```

**Type 1 (Master Audit):**
```
Code=35080, Action=2 (Modify), User=TANYA, Time=2026-02-18 11:44:20
  D1=0, D2=0, D3=0 ← Master record modification
```

---

## Ledger Application Recommendations

### For Balance Queries: Use DailySum

**Query pattern for current balance:**
```sql
SELECT 
    ds.MasterCode1,
    SUM(ds.Dr1) as TotalDebit,
    SUM(ds.Cr1) as TotalCredit,
    SUM(ds.Dr1) - SUM(ds.Cr1) as Balance
FROM DailySum ds
WHERE ds.MasterCode1 = ?
GROUP BY ds.MasterCode1
```

**Query pattern for date range balance:**
```sql
SELECT 
    ds.Date,
    ds.Dr1,
    ds.Cr1,
    ds.Dr1 - ds.Cr1 as Net
FROM DailySum ds
WHERE ds.MasterCode1 = ?
  AND ds.Date BETWEEN ? AND ?
ORDER BY ds.Date
```

### For Audit Trail: Use CheckList

**Query pattern for voucher history:**
```sql
SELECT *
FROM CheckList
WHERE Type = 2
  AND Code = ?  -- VchCode
ORDER BY ActionTime DESC
```

**Query pattern for user activity:**
```sql
SELECT 
    UserName,
    COUNT(*) as Actions,
    SUM(D3) as TotalAmount
FROM CheckList
WHERE Type = 2
  AND ActionTime >= ?
GROUP BY UserName
```

---

## Conclusion

### DailySum
- **Purpose**: Pre-calculated daily running balances per master
- **Use case**: Instant balance inquiries without transaction aggregation
- **Data freshness**: Aggregated from Tran1-Tran12 tables
- **Key insight**: One row per master per day = efficient storage

### CheckList
- **Purpose**: Audit trail for data integrity and compliance
- **Use case**: Track who modified what vouchers/masters and when
- **Key insight**: Type 2 + D3 = quick access to voucher amounts by date range

### Combined Usage
For a complete ledger view, join:
1. **DailySum** - for daily balances
2. **CheckList** - for modification history
3. **Master** - for account names
4. **Tran1-Tran12** - for detailed transaction lines (if needed)

These tables significantly optimize ledger queries by providing pre-aggregated data instead of requiring real-time calculations over transaction tables.
