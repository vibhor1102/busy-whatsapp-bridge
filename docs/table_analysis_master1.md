# Master1 Table Analysis - Busy Accounting Database

**Database:** `C:\Users\Vibhor\Desktop\COMP0012\db12025.bds`  
**Analysis Date:** 2026-02-23  
**Table:** Master1  
**Total Records:** 12,857  
**Total Columns:** 156

---

## 1. Overview

The Master1 table is the central master data table in Busy Accounting Software, storing all ledger accounts, parties (customers/suppliers), items, and other master entities. It uses a generic column structure with many columns having names like C1-C7, D1-D26, I1-I30, B1-B40, CM1-CM11 that serve different purposes based on the master type.

---

## 2. Master Type Distribution

The MasterType field distinguishes between different types of master records:

| MasterType | Description | Count | Percentage |
|------------|-------------|-------|------------|
| 2 | Party (Customer/Supplier) | 8,031 | 62.46% |
| 6 | Item Master | 4,394 | 34.18% |
| 1 | Ledger Account | 54 | 0.42% |
| 9 | Voucher Type | 43 | 0.33% |
| 14 | Employee | 43 | 0.33% |
| 56 | Custom Type 56 | 42 | 0.33% |
| 5 | Item Category | 33 | 0.26% |
| 21 | Expense Category | 31 | 0.24% |
| 13 | Department | 24 | 0.19% |
| 55 | Custom Type 55 | 20 | 0.16% |
| 22 | Income Category | 14 | 0.11% |
| 30 | Region | 13 | 0.10% |
| 31 | Route | 13 | 0.10% |
| 8 | Godown/Warehouse | 12 | 0.09% |
| 1008 | Custom Type 1008 | 11 | 0.09% |
| 25 | Branch | 9 | 0.07% |
| 12 | Project | 8 | 0.06% |
| 60-68 | Various Custom Types | 32 | 0.25% |

---

## 3. Column Purpose Mapping (Reverse Engineered)

### 3.1 Primary Key and Identification

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **Code** | INTEGER | Primary key - unique identifier for each master |
| **MasterType** | SMALLINT | Type of master (1=Ledger, 2=Party, 6=Item, etc.) |
| **Name** | VARCHAR(40) | Primary display name |
| **Alias** | VARCHAR(40) | Alternate name or code |
| **PrintName** | VARCHAR(60) | Name for printing on documents |
| **NameSL** | VARCHAR(255) | Name in second language |
| **AliasSL** | VARCHAR(255) | Alias in second language |
| **PrintNameSL** | VARCHAR(255) | Print name in second language |

### 3.2 Hierarchy and Relationships

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **ParentGrp** | INTEGER | Parent group code (links to another Master1.Code) |
| **Level** | SMALLINT | Hierarchy level depth |
| **SrNo** | SMALLINT | Serial number within parent |
| **Stamp** | INTEGER | Internal tracking/version stamp |

### 3.3 Opening Balances and Amounts (D1-D26)

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **D1-D6** | FLOAT | Various balance amounts (context-dependent) |
| **D7** | FLOAT | **Current Balance** - Most important for parties/ledgers |
| **D8-D26** | FLOAT | Additional balance fields for different purposes |

**Key Finding:** D7 column contains the current outstanding balance for parties (MasterType = 2).

### 3.4 String Fields (C1-C7) - Contact Information

| Column | Length | Typical Use |
|--------|--------|-------------|
| **C1** | VARCHAR(80) | Address Line 1 / Contact Person |
| **C2** | VARCHAR(80) | Address Line 2 / GST Number |
| **C3** | VARCHAR(255) | Phone Number / Mobile |
| **C4** | VARCHAR(255) | Email Address |
| **C5** | VARCHAR(255) | PAN Number / Additional Contact |
| **C6** | VARCHAR(255) | Website / Additional Info |
| **C7** | VARCHAR(255) | Custom Field / Notes |

**Note:** C2 field has data in 4,643 party records. Usage varies by implementation.

### 3.5 Integer Fields (I1-I30) - Flags and Indicators

| Column | Purpose |
|--------|---------|
| **I1-I5** | Various flags and indicators |
| **I6** | Appears to be a status flag (0 or 1) |
| **I7-I28** | Additional configuration flags |
| **I29-I30** | Extended flags |

### 3.6 Boolean Fields (B1-B40)

| Column Range | Purpose |
|--------------|---------|
| **B1-B40** | Boolean flags for various features and settings |
| **External** | BOOLEAN - Indicates external/imported master |
| **BlockedMaster** | BOOLEAN - Account is blocked |
| **DeactiveMaster** | BOOLEAN - Account is deactivated |
| **SyncStatus** | BOOLEAN - Cloud sync status |
| **TPF1, TPF2** | BOOLEAN - Third-party flags |

### 3.7 Cross-Reference Fields (CM1-CM11)

| Column | Purpose |
|--------|---------|
| **CM1-CM11** | INTEGER - Cross-references to other master codes |

### 3.8 Item-Specific Fields

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **HSNCode** | VARCHAR(255) | HSN/SAC code for items |
| **SENO** | VARCHAR(255) | Serial number for items |
| **M1, M2** | MEMO | Long description fields |

### 3.9 Audit and Metadata Fields

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **CreatedBy** | VARCHAR(20) | User who created the record |
| **CreationTime** | DATETIME | Creation timestamp |
| **ModifiedBy** | VARCHAR(20) | User who last modified |
| **ModificationTime** | DATETIME | Last modification timestamp |
| **AuthorisedBy** | VARCHAR(20) | Authorizing user |
| **AuthorisationTime** | DATETIME | Authorization timestamp |
| **ApprovalStatus** | SMALLINT | Approval workflow status |
| **Source** | SMALLINT | Data source indicator |

### 3.10 Other Fields

| Column | Data Type | Purpose |
|--------|-----------|---------|
| **Notes1, Notes2** | VARCHAR(80) | Short notes |
| **MasterNotes** | MEMO | Detailed notes |
| **BlockedNotes** | MEMO | Notes about blocking |
| **BlockedVchType** | VARCHAR(255) | Voucher types blocked |
| **MasterSeriesGrp** | MEMO | Master series grouping |
| **RejectionStatus** | SMALLINT | Rejection workflow status |
| **L1, L2** | INTEGER | Long integer fields |
| **SelfImageLink** | VARCHAR(255) | Image/document URL |
| **SelfImageName** | VARCHAR(255) | Image file name |
| **OldIdentity** | MEMO | Migration/legacy ID |

---

## 4. Key Findings for Ledger Reconstruction

### 4.1 What Distinguishes Master Types

**MasterType = 1 (Ledger Account):**
- Typically high-level accounting heads
- Often have ParentGrp = 0 or link to main groups
- Examples: "Suspense Account", "Cash-in-hand", "Bank Accounts"

**MasterType = 2 (Party - Customer/Supplier):**
- Most numerous type (8,031 records)
- Business partners with whom transactions occur
- Many have phone numbers embedded in Name field
- Balances stored in D7 column

**MasterType = 6 (Item Master):**
- Product/service items
- Contains HSN codes
- Often linked to item groups (ParentGrp)

### 4.2 Balance Storage

**Primary Balance Column:** D7
- Contains current outstanding balance
- Positive = Receivable (Customer owes you)
- Negative = Payable (You owe supplier)
- Applies primarily to MasterType = 2 (Parties)

**Example:**
```
Code 34857: HARVINDER SINGH TRANSPORT | Balance: 49,612.50
```

### 4.3 Parent-Child Relationships

The Master1 table supports a hierarchical structure:
- **ParentGrp** field links to another Master1.Code
- **Level** indicates depth in hierarchy
- **SrNo** provides ordering within parent

Common parent group codes for parties:
- Code 116: Sundry Debtors
- Code 117: Sundry Creditors
- Code 118: Duties & Taxes

### 4.4 Phone Number Location

**Critical Finding:** Phone numbers are stored in multiple locations:

1. **Master1.Name field** - Many parties have phone numbers as their name
   - Example: "9911207075", "9871823434"

2. **Master1.C3 field** - Intended for phone numbers (based on field size and usage)

3. **BillingDet table** - Complete contact information linked by VchCode
   - MobileNo field contains formatted phone numbers
   - Linked to Master1 through transaction vouchers

**Recommended Query for Payment Reminders:**
```sql
-- Get parties with phone numbers and outstanding balances
SELECT 
    m.Code,
    m.Name,
    m.PrintName,
    m.D7 as Balance,
    m.C3 as PhoneFromC3,
    bd.MobileNo as PhoneFromBilling
FROM Master1 m
LEFT JOIN BillingDet bd ON m.Code = bd.VchCode
WHERE m.MasterType = 2
AND m.D7 <> 0
AND (m.Name LIKE '%[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]%'
     OR m.C3 IS NOT NULL 
     OR bd.MobileNo IS NOT NULL)
```

---

## 5. Sample Data Examples

### 5.1 Party Record (MasterType = 2)

```json
{
  "Code": 34857,
  "MasterType": 2,
  "Name": "HARVINDER SINGH TRANSPORT",
  "Alias": "",
  "PrintName": "HARVINDER SINGH TRANSPORT",
  "ParentGrp": 117,
  "D7": 49612.50,
  "C1": "",
  "C2": "",
  "C3": "",
  "CreatedBy": "Nitin",
  "CreationTime": "2026-01-16T17:22:22"
}
```

### 5.2 Ledger Account (MasterType = 1)

```json
{
  "Code": 110,
  "MasterType": 1,
  "Name": "Suspense Account",
  "Alias": "",
  "PrintName": "",
  "ParentGrp": 0,
  "D7": 0.0,
  "CreatedBy": "",
  "CreationTime": "1899-12-30T00:00:00"
}
```

### 5.3 Item Master (MasterType = 6)

```json
{
  "Code": 34859,
  "MasterType": 6,
  "Name": "BAANI FITTED BEDSHEET",
  "Alias": "075008000850",
  "PrintName": "BAANI FITTED BEDSHEET",
  "ParentGrp": 23743,
  "HSNCode": "630419",
  "D1": 1.0,
  "D2": 2199.0,
  "D3": 850.0
}
```

---

## 6. Useful SQL Queries

### 6.1 Get All Parties with Outstanding Balance

```sql
SELECT 
    m.Code,
    m.Name,
    m.PrintName,
    pg.Name as ParentGroup,
    m.D7 as Balance
FROM Master1 m
LEFT JOIN Master1 pg ON m.ParentGrp = pg.Code
WHERE m.MasterType = 2
AND m.D7 <> 0
ORDER BY ABS(m.D7) DESC
```

### 6.2 Get Party Contact Information

```sql
SELECT 
    m.Code,
    m.Name as PartyName,
    m.PrintName,
    m.C1 as Address1,
    m.C2 as Address2,
    m.C3 as Phone,
    m.C4 as Email,
    m.C5 as PAN_GST,
    bd.MobileNo as BillingPhone,
    bd.Email as BillingEmail,
    bd.GSTNo,
    bd.Address1 as BillAddr1,
    bd.Address2 as BillAddr2
FROM Master1 m
LEFT JOIN BillingDet bd ON m.Code = bd.VchCode
WHERE m.MasterType = 2
```

### 6.3 Get Ledger Hierarchy

```sql
SELECT 
    m.Code,
    m.Name,
    m.MasterType,
    pg.Name as ParentName,
    m.Level
FROM Master1 m
LEFT JOIN Master1 pg ON m.ParentGrp = pg.Code
WHERE m.MasterType = 1
ORDER BY m.ParentGrp, m.SrNo
```

### 6.4 Get Parties by Parent Group

```sql
SELECT 
    pg.Name as GroupName,
    COUNT(*) as PartyCount,
    SUM(m.D7) as TotalBalance
FROM Master1 m
JOIN Master1 pg ON m.ParentGrp = pg.Code
WHERE m.MasterType = 2
GROUP BY pg.Name
ORDER BY PartyCount DESC
```

### 6.5 Search Party by Phone Number

```sql
SELECT 
    m.Code,
    m.Name,
    m.PrintName,
    m.D7 as Balance,
    bd.MobileNo
FROM Master1 m
LEFT JOIN BillingDet bd ON m.Code = bd.VchCode
WHERE m.MasterType = 2
AND (
    m.Name LIKE '%[PHONE]%'
    OR m.C3 LIKE '%[PHONE]%'
    OR bd.MobileNo LIKE '%[PHONE]%'
)
```

### 6.6 Get Active Parties Only

```sql
SELECT 
    m.Code,
    m.Name,
    m.D7 as Balance
FROM Master1 m
WHERE m.MasterType = 2
AND m.BlockedMaster = False
AND m.DeactiveMaster = False
```

---

## 7. Relationships to Other Tables

### 7.1 Transaction Tables (Tran1-Tran12)

- **Relationship:** Master1.Code links to TranX.MasterCode1, MasterCode2, etc.
- **Purpose:** Records all financial transactions
- **Key Fields:** VchCode, MasterCode1 (Debit), MasterCode2 (Credit)

### 7.2 BillingDet Table

- **Relationship:** Master1.Code = BillingDet.VchCode
- **Purpose:** Stores detailed billing/contact information
- **Key Fields:** MobileNo, Email, GSTNo, Address1-4
- **Usage:** Best source for phone numbers and complete contact details

### 7.3 DailySum Table

- **Relationship:** Master1.Code = DailySum.MasterCode1
- **Purpose:** Daily transaction summaries
- **Usage:** For calculating period-wise balances

### 7.4 Folio1 Table

- **Relationship:** Master1.Code referenced
- **Purpose:** Folio/bookkeeping entries
- **Usage:** Detailed account statements

### 7.5 CheckList Table

- **Relationship:** CheckList.Code = Master1.Code
- **Purpose:** Audit trail and check list
- **Fields:** D1-D5 contain summary amounts

---

## 8. Recommendations for Payment Reminders

### 8.1 Phone Number Extraction Strategy

Since phone numbers can be in multiple fields, use this priority:

1. **Primary:** BillingDet.MobileNo (most complete and formatted)
2. **Secondary:** Master1.C3 (if populated)
3. **Tertiary:** Parse Master1.Name for numeric patterns

### 8.2 Balance Threshold Query

```sql
-- Parties with balance > threshold for reminders
SELECT 
    m.Code,
    m.Name as PartyName,
    m.PrintName,
    m.D7 as OutstandingBalance,
    bd.MobileNo,
    bd.Email,
    CASE 
        WHEN m.D7 > 0 THEN 'Receivable'
        WHEN m.D7 < 0 THEN 'Payable'
    END as BalanceType
FROM Master1 m
LEFT JOIN BillingDet bd ON m.Code = bd.VchCode
WHERE m.MasterType = 2
AND ABS(m.D7) > 1000  -- Minimum threshold
AND m.BlockedMaster = False
AND m.DeactiveMaster = False
ORDER BY ABS(m.D7) DESC
```

### 8.3 Party Categories for Targeted Messaging

Based on ParentGrp analysis:
- **Group 116:** Sundry Debtors (Customers who owe you)
- **Group 117:** Sundry Creditors (Suppliers you owe)
- Filter by ParentGrp for targeted campaigns

---

## 9. Data Quality Notes

### 9.1 Common Patterns

- **Phone in Name:** ~200+ records have phone numbers as the name
- **Empty Contact Fields:** C1-C7 are often empty for parties
- **BillingDet Coverage:** ~6,848 records vs 8,031 parties

### 9.2 Data Gaps

- Not all parties have contact information in Master1
- BillingDet provides better contact coverage
- Some legacy records lack proper formatting

### 9.3 Validation Rules

- **MasterType = 2:** Must have ParentGrp > 0
- **Active Records:** BlockedMaster = False AND DeactiveMaster = False
- **Valid Balance:** D7 IS NOT NULL

---

## 10. Summary

The Master1 table is the cornerstone of the Busy Accounting database, storing all master entities in a flexible, type-based structure. For ledger reconstruction and payment reminder systems:

1. **Focus on MasterType = 2** (Parties) for customer/supplier data
2. **Use D7 column** for outstanding balances
3. **Join with BillingDet** for complete contact information
4. **Filter by ParentGrp** for categorization
5. **Check BlockedMaster/DeactiveMaster** for active status

The generic column naming (C1-C7, D1-D26, etc.) requires understanding the context (MasterType) to interpret correctly, but provides flexibility for different master types to store specialized data.

---

*Generated by: Master1 Analysis Tool*  
*Date: 2026-02-23*
