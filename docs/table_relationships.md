# Busy Accounting Database - Table Relationships

**Analysis Date:** 2026-02-23  
**Database:** C:\Users\Vibhor\Desktop\COMP0012\db12025.bds  
**Purpose:** Complete data model analysis for ledger reconstruction

---

## Executive Summary

This document provides a comprehensive analysis of the Busy Accounting database schema, focusing on the relationships between major tables essential for ledger reconstruction. The database uses a hierarchical structure with Master1 as the central reference table, supporting multiple entity types through the MasterType discriminator.

**Key Statistics:**
- **Total Transactions (Tran1):** 15,378
- **Total Line Items (Tran2):** 88,717
- **Average Lines per Transaction:** 5.82
- **Total Party Masters (MasterType=2):** 8,031
- **Billing Details Coverage:** 44.5% (6,848 of 15,378 transactions)

---

## Entity Relationship Diagram

```
Master1 (Code, MasterType)
    |
    +--< Folio1 (MasterCode, MasterType) [1:1] - Balances
    |
    +--< Tran1 (MasterCode1) [1:N] - As primary party
    |
    +--< Tran2 (MasterCode1) [1:N] - As line item account

Tran1 (VchCode)
    |
    +--< Tran2 (VchCode) [1:N] - Line items
    |
    +--< BillingDet (VchCode) [1:1] - Billing details

Help1 (RecType, Code, MasterType)
    +--> Master1 [Reference only]
```

---

## Table Definitions

### 1. Master1 - Master Records

**Primary Key:** (Code, MasterType)  
**Row Count:** 12,857  
**Purpose:** Central repository for all master entities

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| Code | int | Unique identifier within MasterType |
| MasterType | int | Entity type discriminator |
| Name | str | Primary name |
| Alias | str | Alternative name/abbreviation |
| PrintName | str | Name for printing |
| ParentGrp | int | Parent group code |
| CM1-CM11 | int | Custom master reference codes |
| D1-D26 | float | Custom data fields |
| I1-I30 | int | Custom integer fields |
| B1-B40 | bool | Boolean flags |

#### MasterType Values

| Value | Description | Record Count |
|-------|-------------|--------------|
| 2 | Party/Customer | 8,031 |
| 3 | Account/Ledger | 1 |
| 6 | Item/Product | 4,394 |
| 1 | General Master | 54 |
| 5 | Other | 33 |

#### Sample Data

```
Code=34856, Name=9911207075, Alias=, ParentGrp=116
Code=34857, Name=HARVINDER SINGH TRANSPORT, Alias=, ParentGrp=117
Code=34858, Name=9871823434, Alias=, ParentGrp=116
```

---

### 2. Tran1 - Transaction Headers

**Primary Key:** VchCode  
**Row Count:** 15,378  
**Purpose:** Stores transaction header information

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| VchCode | int | Unique transaction identifier (auto-increment) |
| VchType | int | Voucher type code |
| Date | datetime | Transaction date |
| VchNo | str | User-defined voucher number |
| VchSeriesCode | int | Voucher series reference |
| MasterCode1 | int | Primary party/account (FK to Master1.Code) |
| MasterCode2 | int | Secondary party/account |
| Status | int | Transaction status |
| ApprovalStatus | int | Workflow approval state |
| CM1-CM6 | int | Custom master codes |

#### Transaction Flow Example

```
[TRAN1 - Header] VchCode=1, VchNo=AHF-0001, Date=2025-04-01
  MasterCode1=31629, MasterCode2=201, VchType=9
  
  -> [TRAN2 - Line 1] MasterCode1=28805, Value=-24.0
  -> [TRAN2 - Line 1] MasterCode1=31629, Value=-46753.0
  -> [TRAN2 - Line 2] MasterCode1=4, Value=44526.3
```

---

### 3. Tran2 - Transaction Line Items

**Primary Key:** (VchCode, SrNo)  
**Row Count:** 88,717  
**Purpose:** Stores transaction line items (ledger entries)

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| RecType | int | Line item type |
| VchCode | int | FK to Tran1.VchCode |
| SrNo | int | Line number within transaction |
| MasterCode1 | int | Account/party for this line (FK to Master1) |
| MasterCode2 | int | Secondary account |
| Value1 | float | Primary amount (debit/credit) |
| Value2 | float | Secondary amount |
| Value3 | float | Tertiary amount |
| Balance1-3 | float | Running balances |
| ItemBal1-3 | float | Item-wise balances |
| CashFlow | float | Cash flow amount |
| ShortNar | str | Short narration |
| D1-D39 | float | Custom data fields |
| CM1-CM12 | int | Custom master codes |
| ClrDate | datetime | Clearance date |

#### Key Relationships
- **Tran1:** VchCode -> Tran1.VchCode (Many-to-One)
- **Master1:** MasterCode1 -> Master1.Code (Many-to-One for account names)

---

### 4. Folio1 - Balance Table

**Primary Key:** (MasterCode, MasterType)  
**Row Count:** 12,520  
**Purpose:** Stores opening balances and current balances

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| MasterCode | int | FK to Master1.Code |
| MasterType | int | FK to Master1.MasterType |
| D1-D150 | float | Balance fields (150 accounting periods) |
| B1-B12 | bool | Boolean flags |

#### MasterType Distribution

| MasterType | Count | Description |
|------------|-------|-------------|
| 2 | 8,031 | Party balances |
| 6 | 4,394 | Item balances |
| 1 | 54 | General master balances |
| 5 | 33 | Other balances |
| 3 | 1 | Account balances |

#### Balance Reconstruction

```sql
SELECT m.Name, f.D1 as OpeningBalance, f.D4 as CurrentBalance
FROM Master1 m
JOIN Folio1 f ON m.Code = f.MasterCode AND m.MasterType = f.MasterType
WHERE m.MasterType = 2
```

---

### 5. BillingDet - Billing Details

**Primary Key:** VchCode  
**Row Count:** 6,848  
**Purpose:** Stores billing-specific information per transaction

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| VchCode | int | FK to Tran1.VchCode |
| PartyName | str | Billing party name |
| Address1-4 | str | Billing addresses |
| MobileNo | str | Contact phone numbers |
| Email | str | Email address |
| GSTNo | str | GST registration number |
| StateCode | int | State code |
| TypeOfDealer | int | Dealer type (0=Unregistered, 1=Regular, 2=Composition) |
| ITPAN | str | Income Tax PAN |
| FSSAINo | str | FSSAI license number |

#### Coverage Statistics

- **Total Transactions:** 15,378
- **With Billing Details:** 6,848
- **Coverage:** 44.5%

#### Sample Records

```
VchCode=1
  Party: KRISHNA SUITING SHIRTING - BINA
  Mobile: 9575731286,8109412656
  GST: 23CVEPG3875N1Z8
  Voucher: AHF-0001 on 2025-04-01

VchCode=22
  Party: UPHAR EMPORIUM-KARNAL
  Mobile: 9817998176,98960-54400
  GST: 06BEKPC9578J1ZY
  Voucher: AHF-0004 on 2025-04-01
```

---

### 6. Help1 - Master Reference

**Row Count:** 56,435  
**Purpose:** Quick reference for master codes and names

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| RecType | int | Record type category |
| Code | int | Master code |
| MasterType | int | Master type |
| NameAlias | str | Master name |
| ParentGroup | int | Parent group reference |
| MasterSeries | int | Series code |
| Status | int | Status flag |

#### RecType Distribution (Selected)

| RecType | Count | Description |
|---------|-------|-------------|
| 1 | 8,227 | General masters |
| 2 | 55 | Account groups |
| 3 | 7,101 | Voucher types |
| 102 | 8,218 | Party masters |
| 103 | 7,898 | Account masters |
| 107 | 8,226 | Item masters |

---

### 7. Help2 - Additional Reference

**Row Count:** 20,498  
**Purpose:** Additional reference data and descriptions

#### Key Columns

| Column | Type | Purpose |
|--------|------|---------|
| RecType1 | int | Primary type |
| RecType2 | int | Secondary type |
| RecType3 | int | Tertiary type |
| Name | str | Reference name/description |

#### Distribution

| RecType1 | RecType2 | Count | Description |
|----------|----------|-------|-------------|
| 1 | 7 | 6,543 | Item descriptions |
| 1 | 31 | 3,954 | Product names |
| 1 | 12 | 2,434 | Additional details |
| 1 | 13 | 1,082 | Reference data |
| 3 | 202 | 400 | Special references |

---

## Critical Relationships

### Transaction Flow: Tran1 -> Tran2

**Join:** Tran1.VchCode = Tran2.VchCode

```sql
-- Get complete transaction with line items
SELECT 
    t1.VchCode, t1.VchNo, t1.Date,
    t2.SrNo, t2.MasterCode1, t2.Value1, t2.ShortNar
FROM Tran1 t1
LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
WHERE t1.VchCode = ?
ORDER BY t2.SrNo
```

### Party Ledger Construction

**Joins Required:**
1. Master1 -> Folio1: For opening/closing balances
2. Master1 -> Tran1: For transaction headers
3. Tran1 -> Tran2: For line items
4. Tran1 -> BillingDet: For contact details
5. Tran2 -> Master1: For account names

```sql
-- Complete Party Ledger Query
SELECT 
    m.Code as PartyCode,
    m.Name as PartyName,
    f.D1 as OpeningBalance,
    t1.VchCode, t1.VchNo, t1.Date,
    bd.MobileNo, bd.GSTNo,
    t2.SrNo, t2.Value1 as Amount,
    m2.Name as LedgerAccount,
    t2.ShortNar as Narration
FROM Master1 m
LEFT JOIN Folio1 f ON m.Code = f.MasterCode AND m.MasterType = f.MasterType
LEFT JOIN Tran1 t1 ON t1.MasterCode1 = m.Code
LEFT JOIN BillingDet bd ON t1.VchCode = bd.VchCode
LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
LEFT JOIN Master1 m2 ON t2.MasterCode1 = m2.Code
WHERE m.MasterType = 2
  AND m.Code = ?
ORDER BY t1.Date, t1.VchNo, t2.SrNo
```

### Balance Reconstruction

```sql
-- Reconstruct party balance from transactions
SELECT 
    m.Code,
    m.Name,
    f.D1 as OpeningBalance,
    SUM(t2.Value1) as TotalMovement,
    f.D1 + SUM(t2.Value1) as CalculatedBalance,
    f.D4 as StoredBalance
FROM Master1 m
LEFT JOIN Folio1 f ON m.Code = f.MasterCode AND m.MasterType = f.MasterType
LEFT JOIN Tran1 t1 ON t1.MasterCode1 = m.Code
LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
WHERE m.MasterType = 2
  AND t1.Date >= '2025-04-01'  -- Financial year start
GROUP BY m.Code, m.Name, f.D1, f.D4
```

---

## Join Summary Table

| From Table | Join Column | To Table | Join Column | Join Type | Cardinality |
|------------|-------------|----------|-------------|-----------|-------------|
| Master1 | Code, MasterType | Folio1 | MasterCode, MasterType | LEFT | 1:1 |
| Master1 | Code | Tran1 | MasterCode1 | LEFT | 1:N |
| Tran1 | VchCode | Tran2 | VchCode | INNER | 1:N |
| Tran1 | VchCode | BillingDet | VchCode | LEFT | 1:1 |
| Tran2 | MasterCode1 | Master1 | Code | LEFT | N:1 |
| Master1 | CM1-CM11 | Help1 | Code | LEFT | N:1 |

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Party Ledger View                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Master1 (Party)                                            │
│  ├── Code (PK)                                              │
│  ├── MasterType = 2                                         │
│  ├── Name                                                   │
│  └── ParentGrp                                              │
└─────────────────────────────────────────────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Folio1   │    │ Tran1    │    │ Help1    │
│ (Balance)│    │ (Header) │    │ (Ref)    │
└──────────┘    └──────────┘    └──────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌────────┐  ┌──────────┐  ┌──────────┐
   │ Tran2  │  │BillingDet│  │ Help2    │
   │(Lines) │  │(Contact) │  │(Ref)     │
   └────────┘  └──────────┘  └──────────┘
        │
        ▼
   ┌────────┐
   │Master1 │
   │(Account│
   │ Names) │
   └────────┘
```

---

## SQL Query Examples

### 1. Get Party Contact Information

```sql
SELECT 
    m.Code,
    m.Name as PartyName,
    m.Alias,
    bd.MobileNo,
    bd.Email,
    bd.GSTNo,
    bd.Address1,
    bd.Address2,
    bd.Address3
FROM Master1 m
LEFT JOIN (
    SELECT DISTINCT MasterCode1, VchCode
    FROM Tran1
) t ON m.Code = t.MasterCode1
LEFT JOIN BillingDet bd ON t.VchCode = bd.VchCode
WHERE m.MasterType = 2
  AND m.Name LIKE '%UPHAR%'
```

### 2. Account-wise Transaction Summary

```sql
SELECT 
    m.Name as AccountName,
    COUNT(*) as LineItemCount,
    SUM(t2.Value1) as TotalValue
FROM Master1 m
JOIN Tran2 t2 ON m.Code = t2.MasterCode1
JOIN Tran1 t1 ON t2.VchCode = t1.VchCode
WHERE m.MasterType = 3
  AND t1.Date BETWEEN '2025-04-01' AND '2026-03-31'
GROUP BY m.Name
HAVING SUM(t2.Value1) <> 0
ORDER BY ABS(SUM(t2.Value1)) DESC
```

### 3. Voucher Detail with All Line Items

```sql
SELECT 
    t1.VchCode,
    t1.VchNo,
    t1.Date,
    m.Name as PartyName,
    bd.MobileNo,
    t2.SrNo,
    m2.Name as AccountName,
    t2.Value1,
    t2.ShortNar
FROM Tran1 t1
JOIN Master1 m ON t1.MasterCode1 = m.Code
LEFT JOIN BillingDet bd ON t1.VchCode = bd.VchCode
LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
LEFT JOIN Master1 m2 ON t2.MasterCode1 = m2.Code
WHERE t1.VchNo = 'AHF-0001'
ORDER BY t2.SrNo
```

### 4. Party-wise Balance Summary

```sql
SELECT 
    m.Code,
    m.Name,
    f.D1 as OpeningBalance,
    f.D4 as CurrentBalance,
    f.D11 as BalancePeriod1,
    f.D12 as BalancePeriod2
FROM Master1 m
JOIN Folio1 f ON m.Code = f.MasterCode AND m.MasterType = f.MasterType
WHERE m.MasterType = 2
  AND ABS(f.D4) > 0
ORDER BY ABS(f.D4) DESC
```

---

## Important Notes for Ledger Reconstruction

### 1. Composite Primary Keys
- Master1 uses composite PK: (Code, MasterType)
- Always include MasterType in joins with Master1
- Folio1 mirrors this structure

### 2. Transaction Structure
- Tran1 contains header information only
- All financial amounts are in Tran2
- A single transaction can have multiple line items
- Value1 in Tran2 contains debit/credit amounts

### 3. Balance Fields in Folio1
- D1-D150 represent 150 different periods/balance types
- D1 is typically Opening Balance
- D4 is typically Current Balance
- Interpretation depends on MasterType

### 4. BillingDet Coverage
- Only 44.5% of transactions have billing details
- Not all parties have contact information stored
- MobileNo and GSTNo are the most reliable fields

### 5. Data Types and Access SQL
- Use proper parentheses for multiple JOINs in Access SQL
- COUNT(DISTINCT) is not supported - use subqueries
- Date comparisons need proper formatting

### 6. MasterType Filtering
- Always filter by MasterType when querying Master1
- MasterType=2: Parties/Customers
- MasterType=3: Accounts/Ledgers
- MasterType=6: Items/Products

---

## Python Code Example for Ledger Reconstruction

```python
import pyodbc
from datetime import datetime

def get_party_ledger(party_code, start_date=None, end_date=None):
    """
    Retrieve complete party ledger with all details.
    
    Args:
        party_code: Master1.Code for the party
        start_date: Optional start date filter
        end_date: Optional end date filter
    """
    conn = pyodbc.connect(
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        r"DBQ=C:\Users\Vibhor\Desktop\COMP0012\db12025.bds;"
        r"PWD=ILoveMyINDIA;"
    )
    cursor = conn.cursor()
    
    query = """
        SELECT 
            m.Name as PartyName,
            m.Alias as PartyAlias,
            f.D1 as OpeningBalance,
            t1.VchCode,
            t1.VchNo,
            t1.Date as VchDate,
            t1.VchType,
            bd.MobileNo,
            bd.GSTNo,
            bd.Address1,
            bd.Address2,
            t2.SrNo as LineNo,
            t2.Value1 as Amount,
            t2.ShortNar as LineNarration,
            m2.Name as LedgerAccount,
            t2.MasterCode1 as LedgerCode
        FROM (Master1 m
        LEFT JOIN Folio1 f ON m.Code = f.MasterCode AND m.MasterType = f.MasterType)
        LEFT JOIN Tran1 t1 ON t1.MasterCode1 = m.Code
        LEFT JOIN BillingDet bd ON t1.VchCode = bd.VchCode
        LEFT JOIN Tran2 t2 ON t1.VchCode = t2.VchCode
        LEFT JOIN Master1 m2 ON t2.MasterCode1 = m2.Code
        WHERE m.MasterType = 2
          AND m.Code = ?
    """
    
    params = [party_code]
    
    if start_date:
        query += " AND t1.Date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND t1.Date <= ?"
        params.append(end_date)
    
    query += " ORDER BY t1.Date, t1.VchNo, t2.SrNo"
    
    cursor.execute(query, params)
    
    ledger_entries = []
    running_balance = 0
    
    for row in cursor.fetchall():
        entry = {
            'vch_code': row.VchCode,
            'vch_no': row.VchNo,
            'date': row.VchDate,
            'mobile': row.MobileNo,
            'gst': row.GSTNo,
            'line_no': row.LineNo,
            'ledger_account': row.LedgerAccount,
            'amount': row.Amount,
            'narration': row.LineNarration,
            'running_balance': running_balance + (row.Amount or 0)
        }
        ledger_entries.append(entry)
        if row.Amount:
            running_balance += row.Amount
    
    conn.close()
    return {
        'party_name': ledger_entries[0]['party_name'] if ledger_entries else None,
        'opening_balance': ledger_entries[0]['opening_balance'] if ledger_entries else 0,
        'closing_balance': running_balance,
        'entries': ledger_entries
    }
```

---

## Appendix: Complete Table Schemas

### Master1 Schema
```
Code: int (PK)
MasterType: int (PK)
Name: str
Alias: str
PrintName: str
ParentGrp: int
Stamp: int
CM1-CM11: int
D1-D26: float
I1-I30: int
I29-I30: int
Level: int
SrNo: int
B1-B40: bool
External: bool
L1-L2: int
Notes1-2: str
MasterNotes: str
CreatedBy: str
CreationTime: datetime
ModifiedBy: str
ModificationTime: datetime
AuthorisedBy: str
AuthorisationTime: datetime
ApprovalStatus: int
SyncStatus: bool
MasterSeriesGrp: str
Source: int
BlockedMaster: bool
BlockedNotes: str
DeactiveMaster: bool
C1-C7: str
HSNCode: str
SENO: str
M1-M2: str
BlockedVchType: str
TPF1-TPF2: bool
RejectionStatus: int
NameSL: str
AliasSL: str
PrintNameSL: str
SelfImageLink: str
SelfImageName: str
OldIdentity: str
```

### Tran1 Schema
```
VchCode: int (PK)
VchType: int
Date: datetime
StockUpdationDate: datetime
Status: int
VchNo: str
VchSeriesCode: int
MasterCode1: int (FK to Master1)
MasterCode2: int
Stamp: int
AutoVchNo: int
CM1-CM6: int
FormRecAmt: float
FormIssAmt: float
CurConRate: float
VchAmtBaseCur: float
VchSalePurcAmt: float
ExciseApplicable: bool
ExciseDocName: str
ExciseValue: float
ExciseType: int
ExcisableAmount: float
ExciseRate: float
OrgVchAmtBaseCur: float
TEApplicable: bool
TDSApplicable: bool
FormRecStatus: int
FormIssStatus: int
ChallanStatus: int
STApplicable: bool
STType: int
DocPrinted: bool
External: bool
CreatedBy: str
CreationTime: datetime
AuthorisedBy: str
AuthorisationTime: datetime
ModifiedBy: str
ModificationTime: datetime
PriceCategory: int
VATInfo: bool
POSEnabled: bool
AutoGeneratedType: int
VchCancelled: bool
BrokerageMode: int
Brokerage: float
BrokerageAmt: float
TranType: int
FreeQtyUsed: bool
Cancelled: bool
D1: float
ApprovalStatus: int
SyncStatus: bool
Source: int
AuditStatus: int
ExtraExpense: float
ExtraExpenseNar1-2: str
c1: str
Date1-2: datetime
I1-I10: int
B1: bool
TPF1-TPF2: bool
RejectionStatus: int
L1: int
SourceDet: str
NepaliDate: str
NepaliFY: str
CM7: int
TCSApplicable: bool
ReturnStatus: int
ReturnStatusAnnual: int
GSTInfo: bool
GSTRecType: int
InputType: int
GSTRepBasis: int
GSTR2Status: int
CheckSum: str
SyncWithIRD: bool
IsRealtime: bool
ConsignmentType: int
ITCClaimedStatus: int
ITCClaimedMonth: int
EInvIRN: str
EInvAckNo: str
EInvAckDate: datetime
EInvSignedQRCode: str
EInvSignedInvoice: str
EInvSignedInvoice2-5: str
SelfImageLink: str
BusyDocLink: str
SelfImageName: str
BusyDocName: str
GSTR2BStatus: int
GSTR2BMonth: int
GSTR2BYear: int
OldIdentity: str
EcomOrderID: str
MandiStockNotDelivered: bool
```

### Tran2 Schema
```
RecType: int
VchCode: int (PK)
MasterCode1: int (FK to Master1)
MasterCode2: int
SrNo: int (PK)
VchType: int
Date: datetime
VchNo: str
VchSeriesCode: int
Value1-3: float
Balance1-3: float
ItemBal1-3: float
CashFlow: float
ShortNar: str
D1-D39: float
I1: int
CM1-CM12: int
B1-B8: bool
ClrDate: datetime
PriceCategory: int
CFMode: int
C1-C4: str
TranType: int
IsReturnQty: bool
ReconStatus: bool
I2-I10: int
TrackingStatus: int
TrackingNo: str
ConsignmentType: int
ConsignmentCleared: bool
EcomOrderItemID: str
```

### Folio1 Schema
```
MasterCode: int (PK)
MasterType: int (PK)
D1-D150: float
B1-B12: bool
```

### BillingDet Schema
```
VchCode: int (PK)
PartyName: str
Address1-4: str
STNo: str
CSTNo: str
ECCCode: str
ExciseRegNo: str
PLANo: str
Range: str
Division: str
Collectorate: str
MobileNo: str
Email: str
DrugLicenceNo1-2: str
ITPAN: str
StateCode: int
GSTNo: str
TypeOfDealer: int
AdharNo: str
PartyNameSL: str
Address1-4SL: str
FSSAINo: str
UdyamNo: str
MSMEType: int
```

### Help1 Schema
```
RecType: int
NameAlias: str
Code: int
MasterType: int
NameOrAlias: int
AdditionalInfo: str
ParentGroup: int
MasterSeries: int
Status: int
DefaultMCCode: int
AddnInfoBt1-4: str
```

### Help2 Schema
```
RecType1: int
RecType2: int
RecType3: int
Name: str
```

---

## Conclusion

This comprehensive analysis provides all the necessary information for ledger reconstruction in the Busy Accounting database. The key understanding is:

1. **Master1** is the central hub with (Code, MasterType) as composite key
2. **Tran1** stores transaction headers with foreign key to Master1
3. **Tran2** contains all financial amounts with line-by-line details
4. **Folio1** stores balances with 150 period fields
5. **BillingDet** provides contact information for 44.5% of transactions
6. **Help1/Help2** serve as reference tables for codes

Use the provided SQL queries and Python code examples as templates for building ledger reconstruction logic.

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-23  
**Generated by:** analyze_relationships.py
