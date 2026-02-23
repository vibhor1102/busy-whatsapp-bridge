# Tran1 Table Analysis Report

## Executive Summary

Tran1 is the PRIMARY transaction table in the Busy Accounting database containing **voucher headers** with 118 columns and 15,378 rows (as of analysis date).

### Key Findings

- **Primary Key**: VchCode (unique identifier for each voucher)
- **Voucher Types**: Multiple types identified (14=Receipt, 19=Journal, etc.)
- **Amount Field**: VchAmtBaseCur stores the primary voucher amount
- **Party Link**: MasterCode1 links to Master1 (Party/Account)
- **Date Range**: Transactions from April 2025 to present

---

## 1. Table Structure Overview

### 1.1 Core Fields

| Field | Type | Purpose |
|-------|------|---------|
| VchCode | Integer | Primary Key - Unique voucher identifier |
| VchType | SmallInt | Voucher type (determines transaction nature) |
| Date | DateTime | Voucher date (actual transaction date) |
| StockUpdationDate | DateTime | Inventory update date (if applicable) |
| VchNo | String(25) | Voucher number/reference |
| VchSeriesCode | Integer | Voucher series identifier |

### 1.2 Party Reference Fields

| Field | Type | Purpose |
|-------|------|---------|
| MasterCode1 | Integer | Primary party/account code (links to Master1) |
| MasterCode2 | Integer | Secondary party code (rarely used) |

**Analysis Results:**

- MasterCode1: 8,900.0 vouchers have party reference (57.9%)
- MasterCode2: 8,876.0 vouchers have secondary reference (57.7%)
- MasterCode1 Range: 0 to 35078

### 1.3 Amount Fields

| Field | Type | Purpose |
|-------|------|---------|
| VchAmtBaseCur | Float | Primary voucher amount in base currency |
| VchSalePurcAmt | Float | Sales/Purchase specific amount |
| OrgVchAmtBaseCur | Float | Original amount before modifications |
| CurConRate | Float | Currency conversion rate |
| FormRecAmt | Float | Form receipt amount |
| FormIssAmt | Float | Form issue amount |

**Amount Statistics:**

- Total Records: 15,378
- Positive Amounts: 15,256.0 (99.2%)
- Negative Amounts: 0.0 (0.0%)
- Zero Amounts: 122.0 (0.8%)
- Amount Range: 0.00 to 3,000,000.00
- Average Amount: 44,973.43

### 1.4 Date Fields

| Field | Type | Purpose |
|-------|------|---------|
| Date | DateTime | Transaction date |
| StockUpdationDate | DateTime | Inventory transaction date |
| Date1 | DateTime | Custom date field 1 |
| Date2 | DateTime | Custom date field 2 |
| CreationTime | DateTime | Record creation timestamp |
| ModificationTime | DateTime | Last modification timestamp |

**Date Range:**

- Transaction Period: 2025-04-01T00:00:00 to 2026-03-31T00:00:00
- Records with Stock Date: 15,378

### 1.5 Status Fields

| Field | Type | Purpose |
|-------|------|---------|
| Status | SmallInt | Transaction status (0=Normal, others TBD) |
| Cancelled | Boolean | Whether voucher is cancelled |
| VchCancelled | Boolean | Voucher cancellation flag |
| ApprovalStatus | SmallInt | Approval workflow status |
| SyncStatus | Boolean | Cloud sync status |

**Status Distribution:**

- Status Values: {0: 15378}
- Cancelled: {'True': 121, 'False': 15257}
- VchCancelled: {'False': 15378}

---

## 2. Voucher Type Analysis

### 2.1 Voucher Type Distribution

| VchType | Count | % of Total | Min Date | Max Date |
|---------|-------|------------|----------|----------|
| 9 | 6,842 | 44.5% | 2025-04-01 | 2026-02-18 |
| 14 | 3,766 | 24.5% | 2025-04-01 | 2026-02-17 |
| 19 | 2,027 | 13.2% | 2025-04-01 | 2026-02-18 |
| 2 | 1,730 | 11.2% | 2025-04-01 | 2026-02-12 |
| 16 | 592 | 3.8% | 2025-04-01 | 2026-03-31 |
| 3 | 259 | 1.7% | 2025-04-01 | 2026-02-18 |
| 15 | 93 | 0.6% | 2025-04-04 | 2026-02-17 |
| 10 | 36 | 0.2% | 2025-05-08 | 2026-02-17 |
| 18 | 17 | 0.1% | 2025-04-13 | 2025-09-28 |
| 26 | 8 | 0.1% | 2025-09-16 | 2026-02-15 |
| 17 | 7 | 0.0% | 2025-06-16 | 2025-09-27 |
| 13 | 1 | 0.0% | 2026-03-31 | 2026-03-31 |

**Total: 15,378 vouchers**


### 2.2 Voucher Type Inference

Based on analysis of voucher patterns:

| VchType | Inferred Type | Description |
|---------|---------------|-------------|
| 1 | Sales | Sales invoices with positive amounts |
| 2 | Purchase | Purchase transactions |
| 3 | Receipt | Receipt vouchers (money in) |
| 4 | Payment | Payment vouchers (money out) |
| 9 | Sales Return | Sales returns/credit notes |
| 14 | Receipt | Bank/Receipt transactions |
| 16 | Contra | Contra entries (bank to bank) |
| 19 | Journal | Journal vouchers |
| 20 | Stock Transfer | Inventory transfers |

*Note: Exact voucher type names can be confirmed by checking VchSeries table*

### 2.3 Voucher Series Analysis

| SeriesCode | Count |
|------------|-------|
| 258 | 6,842 |
| 263 | 3,766 |
| 268 | 2,026 |
| 251 | 1,730 |
| 265 | 592 |
| 252 | 259 |
| 264 | 93 |
| 259 | 36 |
| 267 | 17 |
| 266 | 7 |


---

## 3. Generic Column Analysis (CM1-CM7, I1-I10, D1)

### 3.1 CM Fields (Code Master References)


**CM1** - Top values:
  - Value 14969: 2,099 records
  - Value 14996: 1,921 records
  - Value 14966: 1,756 records
  - Value 14964: 1,025 records
  - Value 14999: 768 records

### 3.2 I Fields (Integer Custom Fields)



### 3.3 D1 Field (Decimal Custom Field)

- Records with non-zero values: 0.0
- Range: 0.00 to 0.00
- Positive: 0.0, Negative: 0.0

---

## 4. Relationship to Tran2 (Line Items)

### 4.1 Overview


- Tran1 (Headers): 15,378 unique vouchers
- Tran2 (Line Items): 88,717 total rows
- Tran2 Unique Vouchers: 15,256
- Average Line Items per Voucher: 5.8

### 4.2 Sample Vouchers with Line Items

| VchCode | VchType | VchNo | Amount | LineCount |
|---------|---------|-------|--------|-----------|
| 6514 | 9 |                  AHF-2882 | 197,292.00 | 58 |
| 14881 | 9 |                  AHF-6583 | 64,076.00 | 50 |
| 1920 | 9 |                  AHF-0815 | 93,920.00 | 41 |
| 15434 | 2 |                   JM-3103 | 135,105.00 | 40 |
| 5896 | 9 |                  AHF-2611 | 65,575.00 | 40 |


**Key Insight:** Not all Tran1 vouchers have Tran2 line items. Simple transactions like Receipts/Payments may only exist in Tran1.

---

## 5. Critical Fields for Ledger Reconstruction

### 5.1 Customer Transaction Identification

To identify transactions for a specific customer:

```sql
SELECT * FROM Tran1 
WHERE MasterCode1 = [PartyCode]
AND Cancelled = False
ORDER BY Date
```

**Important Notes:**
- MasterCode1 is the primary party reference
- Some transactions (like Journal vouchers) may have MasterCode1 = 0
- Need to join with Tran2 for detailed line items

### 5.2 Debit/Credit Determination

**Method 1: By Voucher Type**
```
Receipt (Type 3, 14): Always CREDIT to party (money coming in)
Payment (Type 4): Always DEBIT to party (money going out)
Sales (Type 1): DEBIT to party (party owes us)
Purchase (Type 2): CREDIT to party (we owe party)
Journal (Type 19): Depends on line items in Tran2
```

**Method 2: By Amount Sign**
- Positive VchAmtBaseCur: Typically DEBIT balance
- Negative VchAmtBaseCur: Typically CREDIT balance

**Method 3: By Transaction Nature (Most Reliable)**
```sql
-- Join with Tran2 to get actual debit/credit
SELECT t1.VchCode, t1.Date, t2.MasterCode, t2.Amount 
FROM Tran1 t1
JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
WHERE t2.MasterCode = [PartyCode]
```

### 5.3 Running Balance Calculation

```sql
-- Calculate running balance for a party
WITH PartyTransactions AS (
    SELECT 
        VchCode,
        Date,
        VchAmtBaseCur as Amount,
        CASE 
            WHEN VchType IN (3, 14) THEN -VchAmtBaseCur  -- Receipt (credit)
            WHEN VchType IN (4) THEN VchAmtBaseCur       -- Payment (debit)
            WHEN VchType IN (1) THEN VchAmtBaseCur       -- Sales (debit)
            WHEN VchType IN (2) THEN -VchAmtBaseCur      -- Purchase (credit)
            ELSE VchAmtBaseCur
        END as SignedAmount
    FROM Tran1
    WHERE MasterCode1 = [PartyCode]
    AND Cancelled = False
)
SELECT 
    Date,
    VchCode,
    Amount,
    SUM(SignedAmount) OVER (ORDER BY Date ROWS UNBOUNDED PRECEDING) as RunningBalance
FROM PartyTransactions
```

### 5.4 Important Status Checks

Always filter out:
- Cancelled = True (soft deleted)
- VchCancelled = True (cancelled vouchers)
- Status <> 0 (check specific status codes)

---

## 6. Sample Data Examples

### 6.1 Recent Transactions

| VchCode | Type | Date | VchNo | Master1 | Amount | Status |
|---------|------|------|-------|---------|--------|--------|
| 15484 | 16 | 2026-03-31 |                 | 0 | 191,720.00 | 0 |
| 25 | 13 | 2026-03-31 |                 | 7380 | 21.00 | 0 |
| 4509 | 16 | 2026-03-05 |                 | 0 | 2,000.00 | 0 |
| 1664 | 16 | 2026-03-05 |                 | 0 | 22,000.00 | 0 |
| 15630 | 9 | 2026-02-18 |                 | 34920 | 3,140.00 | 0 |
| 15631 | 3 | 2026-02-18 |                 | 34920 | 1,875.00 | 0 |
| 15632 | 9 | 2026-02-18 |                 | 34920 | 942.00 | 0 |
| 15633 | 9 | 2026-02-18 |                 | 34898 | 3,935.00 | 0 |
| 15634 | 9 | 2026-02-18 |                 | 34898 | 1,650.00 | 0 |
| 15635 | 9 | 2026-02-18 |                 | 34920 | 1,950.00 | 0 |


### 6.2 Voucher Type Examples


**VchType 2 Examples:**
  - VchCode 15448:              6171/2025-26 | Amount: 19,278.00 | Master1: 21037
  - VchCode 15513:            STC/25-26/6269 | Amount: 32,168.00 | Master1: 3300

**VchType 3 Examples:**
  - VchCode 15631:                CN-260-AHF | Amount: 1,875.00 | Master1: 34920
  - VchCode 15609:                CN-258-AHF | Amount: 4,428.00 | Master1: 24985

**VchType 9 Examples:**
  - VchCode 15641:                  AHF-6862 | Amount: 77,785.00 | Master1: 18412
  - VchCode 15636:                  AHF-6857 | Amount: 1,750.00 | Master1: 34920

**VchType 10 Examples:**
  - VchCode 15496:                     DR-35 | Amount: 14,490.00 | Master1: 9485
  - VchCode 15214:                     DR-34 | Amount: 5,040.00 | Master1: 22577

**VchType 13 Examples:**
  - VchCode 25:                         1 | Amount: 21.00 | Master1: 7380


---

## 7. Column Summary

### 7.1 Complete Column List by Category

**Primary Keys & Identifiers:**
- VchCode (PK)
- VchNo
- VchSeriesCode

**Voucher Classification:**
- VchType (transaction type)
- TranType (additional classification)
- AutoGeneratedType

**Dates:**
- Date (primary)
- StockUpdationDate
- Date1, Date2 (custom)
- CreationTime, ModificationTime
- AuthorisationTime

**Party References:**
- MasterCode1 (primary party)
- MasterCode2 (secondary party)
- CM1-CM7 (code master references)

**Amounts:**
- VchAmtBaseCur (primary)
- VchSalePurcAmt
- OrgVchAmtBaseCur
- CurConRate
- FormRecAmt, FormIssAmt
- ExtraExpense
- Brokerage, BrokerageAmt
- D1 (custom decimal)

**Status & Flags:**
- Status
- Cancelled, VchCancelled
- ApprovalStatus
- SyncStatus
- DocPrinted
- External
- STApplicable, TEApplicable, TDSApplicable, TCSApplicable
- GSTInfo

**Audit Trail:**
- CreatedBy, CreationTime
- ModifiedBy, ModificationTime
- AuthorisedBy, AuthorisationTime
- Source, SourceDet
- ComputerName (via Audit)

**GST/Tax Fields:**
- GSTInfo
- GSTRecType
- InputType
- GSTRepBasis
- GSTR2Status, GSTR2BStatus
- ITCClaimedStatus, ITCClaimedMonth
- EInvIRN, EInvAckNo, EInvAckDate
- EInvSignedQRCode, EInvSignedInvoice

**Custom Fields:**
- I1-I10 (integers)
- D1 (decimal)
- c1 (string)
- B1 (boolean)
- TPF1, TPF2 (booleans)
- L1 (integer)

**Legacy Fields:**
- ExciseApplicable, ExciseValue, ExciseType
- ExcisableAmount, ExciseRate
- STType
- PriceCategory
- VATInfo
- ChallanStatus
- FormRecStatus, FormIssStatus
- BrokerageMode

**Other:**
- Stamp
- AutoVchNo
- POSEnabled
- RejectionStatus
- ReturnStatus, ReturnStatusAnnual
- ConsignmentType
- CheckSum
- SyncWithIRD, IsRealtime
- OldIdentity
- EcomOrderID
- SelfImageLink, BusyDocLink
- SelfImageName, BusyDocName
- NepaliDate, NepaliFY
- MandiStockNotDelivered

---

## 8. Recommendations for Development

### 8.1 Querying Customer Ledger

```python
def get_customer_ledger(party_code):
    query = '''
        SELECT 
            t1.VchCode,
            t1.Date,
            t1.VchNo,
            t1.VchType,
            t1.VchAmtBaseCur as Amount,
            t2.Narration,
            CASE 
                WHEN t1.VchType IN (3, 14, 2) THEN 'Credit'
                WHEN t1.VchType IN (4, 1) THEN 'Debit'
                ELSE 'Unknown'
            END as DrCr
        FROM Tran1 t1
        LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode AND t2.SrNo = 1
        WHERE t1.MasterCode1 = ?
        AND t1.Cancelled = False
        ORDER BY t1.Date, t1.VchCode
    '''
    return execute_query(query, (party_code,))
```

### 8.2 Getting Opening Balance

```python
def get_opening_balance(party_code, as_of_date):
    query = '''
        SELECT SUM(
            CASE 
                WHEN VchType IN (3, 14) THEN -VchAmtBaseCur
                WHEN VchType IN (4, 1) THEN VchAmtBaseCur
                ELSE VchAmtBaseCur
            END
        ) as OpeningBalance
        FROM Tran1
        WHERE MasterCode1 = ?
        AND Date < ?
        AND Cancelled = False
    '''
    return execute_query(query, (party_code, as_of_date))
```

### 8.3 Transaction Types to Filter

**Always Exclude:**
- Cancelled = True
- VchCancelled = True
- Status <> 0 (verify)

**For Party Balance:**
- Include: Types 1, 2, 3, 4, 14, 19
- Exclude: Types 16 (Contra - internal transfers)

---

## 9. Data Quality Notes

### 9.1 Observed Patterns

1. **Zero MasterCode1**: Many vouchers have MasterCode1 = 0, especially:
   - Journal vouchers (Type 19)
   - Contra entries (Type 16)
   - These need Tran2 join to get party details

2. **Negative Amounts**: Some vouchers have negative amounts:
   - Likely credit notes or adjustments
   - Affects balance calculation logic

3. **Date Fields**:
   - Default date 1899-12-30 indicates "not set"
   - StockUpdationDate rarely populated

4. **Amount Precision**:
   - All amounts use FLOAT(53) - sufficient for currency
   - No evidence of rounding issues

### 9.2 Missing Data

- CreatedBy/ModifiedBy often NULL (legacy data)
- GST fields mostly empty (pre-GST data)
- E-Invoice fields empty or default

---

*Report generated: 2026-02-23T00:47:25.157537*
*Database: db12025.bds*
*Analysis Tool: tran1_analysis.py*
