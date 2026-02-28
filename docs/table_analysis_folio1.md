# Folio1 Table Analysis Report

**Analysis Date:** 2026-02-23 00:46:48
**Database:** Busy Accounting Software (db12025.bds)
**Table:** Folio1

## Executive Summary

Folio1 is the **CRITICAL** table for account balance reconstruction in Busy Accounting Software.
This table serves as the ledger folio storage with running balances for all accounts.

### Key Statistics:
- **Total Columns:** 164 (MasterCode, MasterType, D1-D150, B1-B12)
- **Total Rows:** 12,520 account records
- **MasterTypes:** 8 different account categories

## Table Structure Analysis

### Column Layout:

| Column | Type | Purpose |
|--------|------|---------|
| **MasterCode** | Integer | Foreign key to Master1.Code - Account identifier |
| **MasterType** | Integer | Account category/classification |
| **D1-D150** | Float (Decimal) | 150 balance/amount storage columns |
| **B1-B12** | Boolean | 12 flag columns (unknown purpose) |

## MasterType Distribution

Accounts are categorized by MasterType:

| MasterType | Count | Description |
|------------|-------|-------------|
| 1 | 54 | Account Category 1 |
| 2 | 8,031 | Account Category 2 |
| 3 | 1 | Account Category 3 |
| 5 | 33 | Account Category 5 |
| 6 | 4,394 | Account Category 6 |
| 10 | 4 | Account Category 10 |
| 28 | 2 | Account Category 28 |
| 34 | 1 | Account Category 34 |

## D Column Balance Analysis

The D1-D150 columns contain balance/amount data. Analysis of first 20 columns:

| Column | Accounts with Values | Min Value | Max Value |
|--------|---------------------|-----------|-----------|
| D1 | 2,670.0 | -69,673,581.01 | 39,796,810.65 |
| D2 | 2,325.0 | -2,110.00 | 11,727.00 |
| D3 | 2,306.0 | -808,158.10 | 4,376,550.03 |
| D17 | 837.0 | -82.00 | 33,287,758.20 |
| D18 | 716.0 | -525.00 | 29,078,792.38 |
| D16 | 592.0 | 0.00 | 28,446,397.60 |
| D19 | 569.0 | -105.00 | 22,684,479.93 |
| D15 | 542.0 | 0.00 | 22,988,785.99 |
| D14 | 437.0 | 0.00 | 14,460,721.51 |
| D11 | 434.0 | 0.00 | 19,047,460.68 |
| D13 | 410.0 | -7.00 | 12,575,382.40 |
| D20 | 402.0 | -585.00 | 16,923,710.00 |
| D12 | 400.0 | 0.00 | 20,302,314.03 |
| D4 | 391.0 | -191,132,169.82 | 194,976,096.86 |
| D5 | 1.0 | -239,238.88 | 0.00 |
| D6 | 1.0 | 0.00 | 7,660,060.67 |

## Sample Balance Data

Examples of accounts with non-zero balances:

| MasterCode | MasterType | D1 | D2 | D3 | D4 | D5 |
|------------|------------|----|----|----|----|----|
| 1 | 2 | -298,649.72 | 0.00 | 0.00 | -298,649.72 | 0.00 |
| 3 | 2 | -34,940,200.00 | 0.00 | 0.00 | -34,940,200.00 | 0.00 |
| 4 | 2 | 0.00 | 0.00 | 0.00 | 194,976,096.86 | 0.00 |
| 5 | 2 | 0.00 | 0.00 | 0.00 | -191,132,169.82 | 0.00 |
| 101 | 1 | 9,291,248.26 | 0.00 | 0.00 | 9,291,248.26 | 0.00 |
| 102 | 1 | -69,673,581.01 | 0.00 | 0.00 | -69,673,581.01 | 0.00 |
| 103 | 1 | 22,737,089.37 | 0.00 | 0.00 | 22,737,089.37 | 0.00 |
| 104 | 1 | -2,151,567.27 | 0.00 | 0.00 | -2,151,567.27 | 0.00 |
| 106 | 1 | 39,796,810.65 | 0.00 | 0.00 | 39,796,810.65 | 0.00 |
| 108 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | -239,238.88 |

## Accounts with Outstanding Balances (Mobile Available)

These accounts have mobile numbers and can receive WhatsApp payment reminders:

| Code | Account Name | Mobile | Balance |
|------|--------------|--------|---------|
| 4 | Account 4 | N/A | 194,976,096.86 |
| 123 | Account 123 | N/A | 194,976,096.86 |
| 5 | Account 5 | N/A | -191,132,169.82 |
| 122 | Account 122 | N/A | -191,132,169.82 |
| 102 | Account 102 | N/A | -139,347,162.02 |
| 106 | Account 106 | N/A | 79,593,621.30 |
| 3 | Account 3 | N/A | -69,880,400.00 |
| 115 | Account 115 | N/A | -69,880,400.00 |
| 116 | Account 116 | N/A | -56,924,391.00 |
| 120 | Account 120 | N/A | 49,053,595.42 |
| 103 | Account 103 | N/A | 45,474,178.74 |
| 117 | Account 117 | N/A | 45,309,880.00 |
| 128 | Account 128 | N/A | 29,910,517.88 |
| 101 | Account 101 | N/A | 18,582,496.52 |
| 125 | Account 125 | N/A | -8,157,347.86 |
| 108 | Account 108 | N/A | 7,420,821.79 |
| 109 | Account 109 | N/A | -5,637,751.28 |
| 114 | Account 114 | N/A | -5,384,540.00 |
| 104 | Account 104 | N/A | -4,303,134.54 |
| 1024 | Account 1024 | N/A | -2,159,477.00 |
| 1014 | Account 1014 | N/A | -1,364,608.08 |
| 124 | Account 124 | N/A | -1,037,464.65 |
| 121 | Account 121 | N/A | 629,508.00 |
| 1 | Account 1 | N/A | -597,299.44 |
| 111 | Account 111 | N/A | -597,299.44 |
| 1025 | Account 1025 | N/A | -368,940.00 |
| 112 | Account 112 | N/A | -358,169.76 |
| 127 | Account 127 | N/A | -286,865.81 |
| 1205 | Account 1205 | N/A | -286,865.81 |
| 1212 | Account 1212 | N/A | -220,518.32 |

## Balance Structure Theory

### Hypothesis: Multi-Dimensional Balance Storage

Based on data analysis, the D1-D150 columns likely represent:

**Option 1: Monthly Balance History**
- D1-D12: Month 1-12 balances for current year
- D13-D24: Month 1-12 balances for previous year
- Supports up to 12.5 years of history (150 ÷ 12 = 12.5)

**Option 2: Multi-Metric Storage**
- D1: Opening Balance
- D2-D11: Monthly summaries or different metrics
- D12: Closing Balance
- Pattern repeats for multiple years

**Option 3: Account Type Specific**
- Different D columns used based on MasterType
- Some columns for debtors, others for creditors, etc.

## How Opening/Closing Balances Work

### Finding Opening Balance:
```sql
-- Sum of early D columns (D1-D5) often represents opening/current balance
SELECT MasterCode, (D1 + D2 + D3 + D4 + D5) AS opening_balance
FROM Folio1
WHERE MasterCode = [AccountCode]
```

### Finding Current/Closing Balance:
```sql
-- Sum of relevant period columns
SELECT MasterCode,
       (COALESCE(D1,0) + COALESCE(D2,0) + ... + COALESCE(D20,0)) AS current_balance
FROM Folio1
WHERE MasterCode = [AccountCode]
```

## Party-wise Balance for Payment Reminders

### SQL Query to Extract Party Balances:
```sql
SELECT 
    m.Code,
    m.MasterName1 AS account_name,
    m.Mobile,
    m.Email,
    (COALESCE(f.D1,0) + COALESCE(f.D2,0) + COALESCE(f.D3,0) + 
     COALESCE(f.D4,0) + COALESCE(f.D5,0) + COALESCE(f.D6,0) + 
     COALESCE(f.D7,0) + COALESCE(f.D8,0) + COALESCE(f.D9,0) + 
     COALESCE(f.D10,0)) AS outstanding_balance
FROM Master1 m
LEFT JOIN Folio1 f ON m.Code = f.MasterCode
WHERE m.Mobile IS NOT NULL
  AND m.Mobile <> ''
  AND ABS(COALESCE(f.D1,0) + COALESCE(f.D2,0)) > 0
ORDER BY ABS(outstanding_balance) DESC
```

### Python Implementation:
```python
def get_party_balance(master_code):
    """Get current balance for a party"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT D1, D2, D3, D4, D5, D6, D7, D8, D9, D10
        FROM Folio1
        WHERE MasterCode = ?
    ''', (master_code,))
    
    row = cursor.fetchone()
    if row:
        balance = sum([float(v) if v else 0 for v in row])
        return balance
    return 0
```

## Debit vs Credit Analysis

Based on sample data:
- **Positive values** in D columns = Debit balances
- **Negative values** in D columns = Credit balances
- Zero values = No activity in that period/metric

Example from data:
- MasterCode 1008: D1 = -9712.41 (Credit balance of ₹9,712.41)
- MasterCode 1009: D11 = 49260.00 (Debit balance of ₹49,260)

## Relationship to Master1

Folio1 links to Master1 through:
- **Folio1.MasterCode** = **Master1.Code** (Primary Key)

To get complete party information:
```sql
SELECT 
    f.MasterCode,
    m.MasterName1,
    m.Mobile,
    m.Email,
    m.MasterTypeName1,
    f.D1, f.D2, f.D3  -- Balance columns
FROM Folio1 f
INNER JOIN Master1 m ON f.MasterCode = m.Code
WHERE f.MasterCode = [SpecificCode]
```

## Recommendations

### For WhatsApp Payment Reminders:
1. **Query Pattern:** Join Folio1 with Master1 on MasterCode=Code
2. **Balance Calculation:** Sum D1-D10 for most current balance
3. **Mobile Validation:** Always check Master1.Mobile IS NOT NULL
4. **Amount Formatting:** Use absolute value with Dr/Cr indicator
5. **Filter:** Only send reminders for balances above threshold (e.g., ₹1000)

### For Ledger Reconstruction:
1. **Opening Balance:** Use D1 or sum of first few D columns
2. **Current Balance:** Sum of all relevant D columns
3. **Period Filtering:** Filter by MasterType for specific ledgers
4. **Data Integrity:** Handle NULL values with COALESCE

## Data Quality Summary

- **Total Accounts:** 12,520
- **MasterTypes:** 8 categories
- **Active Balance Columns:** 16 (in first 20 analyzed)
- **Accounts with Mobile:** 42 have mobile numbers
- **Accounts with Balances:** 42 have non-zero balances

---

*Report generated by Folio1 Analysis Tool*
*Database: C:\Users\Vibhor\Desktop\COMP0012\db12025.bds*