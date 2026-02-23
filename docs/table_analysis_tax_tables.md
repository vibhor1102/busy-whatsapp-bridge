# GST/Tax Tables Analysis Report

**Database:** `C:\Users\Vibhor\Desktop\COMP0012\db12025.bds`  
**Analysis Date:** February 23, 2026  
**Analysis Tool:** 32-bit Python with MS Access ODBC Driver

---

## Executive Summary

This report analyzes all GST and Tax-related tables in the Busy Accounting database. The analysis reveals critical insights into tax data storage, GST return filing status, and transaction-level tax calculations.

### Key Findings

- **4 tables with data:** VchGSTSumItemWise (26,159 rows), GSTR2BInfo (3,650 rows), GSTR2AInfo (3,101 rows), GSTR3BInfo (37 rows)
- **3 empty tables:** GSTInfo, GSTR1Info, VATInfo (structure present but no data)
- **Primary tax data source:** VchGSTSumItemWise contains item-level tax calculations
- **GSTR2A/B tables:** Store auto-populated return data from GST portal (ITC tracking)

---

## Tables with Data

### 1. VchGSTSumItemWise (26,159 rows, 52 columns)

**Purpose:** Item-level transaction tax details - the PRIMARY source for transaction tax data

#### Key Columns

| Category | Columns |
|----------|---------|
| **Transaction Keys** | VchCode, ItemCode, ItemSrNo, VchNo, VchDate, VchType, VchSeriesCode |
| **Party Info** | PartyCode, PartyStateTinDigit, PartyStateCode |
| **Tax Details** | TaxCatCode, STPTCode, TaxRate, TaxRate1, TaxAmt, TaxAmt1 |
| **HSN/Classification** | HSNCode, SENo, RecType, GSTRepBasis |
| **Amounts** | TaxableAmt, ActualSaleAmt, SurchargeAmt, ACessAmt, StateCessAmt |
| **GSTR2B Tracking** | GSTR2BStatus, GSTR2BMonth, GSTR2BYear, ITCClaimedStatus, ITCClaimedMonth |
| **Location** | POSStateCode, POSStateTinDigit, BDStateCode, BDStateTinDigit, LocType |

#### Data Analysis

- **Total Taxable Amount:** ₹306,476,041.19
- **Unique Transactions:** 8,857 (average 3.0 items per transaction)
- **Voucher Types:** Primarily Type 9 (Sales), Type 3 (Credit Notes)
- **Date Range:** Current financial year (2025-2026)

#### Tax Structure

The table uses a dual-tax-rate structure:
- **TaxRate/TaxAmt** - Primary tax component (typically CGST)
- **TaxRate1/TaxAmt1** - Secondary tax component (typically SGST)

For IGST transactions, both rates are combined.

#### HSN Code Distribution (Top 10)

Common HSN codes observed in the data:
- 63041930, 63041910, 63014000 (Textile products)
- 63049289, 63026090 (Made-ups)
- 570310 (Carpets)
- 94044040 (Furniture)

#### ITC Tracking

The table includes GSTR2B integration fields:
- `GSTR2BStatus` - Whether transaction appears in GSTR2B
- `GSTR2BMonth/Year` - Return period
- `ITCClaimedStatus` - ITC claim status
- `ITCClaimedMonth` - Month when ITC was claimed

**Link to Transactions:** 
- **VchCode** links to VchMaster (voucher header)
- **ItemCode** links to ItemMaster (item details)
- **PartyCode** links to MasterMaster (party details)

---

### 2. GSTR2AInfo (3,101 rows, 54 columns)

**Purpose:** Auto-populated GSTR-2A data from GST portal (purchase invoices uploaded by suppliers)

#### Key Columns

| Category | Columns |
|----------|---------|
| **Identity** | RecType, TranType, Month, Year, SrNo |
| **GST Numbers** | GSTIN (supplier), CompGSTIN (company: 06AKOPG5313N1ZX) |
| **Invoice Details** | Date, VchNo, OrgDate, OrgVchNo, InvType |
| **Amounts** | TotalAmt, TaxableAmt, Rate |
| **Tax Breakdown** | CGST, SGST, IGST, CessAmt |
| **ITC Details** | ITCCGST, ITCSGST, ITCIGST, ITCCessAmt, ITCElg, ITCAvl |
| **Location** | POS (0=Intra-state, 6=Inter-state for Haryana) |
| **Status** | CFS (Counter Party Filing Status), CheckSum |
| **Supplier Info** | TradeName, SupplierFilDate, SupplierPrd |

#### Data Analysis

- **Date Range:** May 27, 2024 to November 30, 2025
- **Total Amount:** ₹124,129,993.40
- **Taxable Value:** ₹116,888,120.78
- **CGST Total:** ₹2,046,278.74
- **SGST Total:** ₹2,046,278.74
- **IGST Total:** ₹3,150,080.04

#### Record Types

- **Type 1:** 1,478 records (Header records with CheckSum)
- **Type 2:** 1,623 records (Line items with tax details)

#### POS Distribution

- **POS 0:** 1,655 records (Intra-state transactions - local purchases)
- **POS 6:** 1,444 records (Inter-state transactions - Haryana)
- **POS 3, 8:** 2 records (Other states)

#### Supplier Filing Periods

The data includes supplier filing dates and periods:
- **SupplierPrd:** Format like "Apr-25", "May-25" 
- **SupplierFilDate:** When supplier filed their GSTR-1

**Business Use:** Track ITC available from suppliers' filings. RecType 1 = invoice header, RecType 2 = tax line items.

---

### 3. GSTR2BInfo (3,650 rows, 54 columns)

**Purpose:** Auto-drafted ITC statement from GST portal (static monthly statement for ITC claims)

#### Key Differences from GSTR2A

GSTR2B is a static monthly statement, while GSTR2A is dynamic. Key additional columns:
- **TradeName** - Supplier's trade name
- **Reason** - ITC availability reason codes
- **ITCAvl** - Boolean flag for ITC availability

#### Data Analysis

- **Date Range:** May 27, 2024 to January 31, 2026
- **Total Amount:** ₹151,647,103.56
- **Taxable Value:** ₹143,045,493.77
- **CGST Total:** ₹2,378,295.71
- **SGST Total:** ₹2,378,295.71
- **IGST Total:** ₹3,851,256.31

#### Record Types

- **Type 1:** 1,825 records (Invoice headers)
- **Type 2:** 1,825 records (Line items with tax breakdown)

#### POS Distribution

- **POS 0:** 1,871 records (Intra-state)
- **POS 6:** 1,777 records (Inter-state)
- **POS 3, 8:** 2 records

#### ITC Availability

- **ITCAvl = True:** Available for claiming
- **Reason codes** indicate why ITC is available or not

**Business Use:** Primary table for ITC reconciliation and monthly return filing (GSTR-3B).

---

### 4. GSTR3BInfo (37 rows, 33 columns)

**Purpose:** GSTR-3B monthly return summary data

#### Key Columns

| Category | Columns |
|----------|---------|
| **Period** | RecType, TranType, Month, Year |
| **GSTIN** | GSTIN, Type |
| **Outward Supplies** | TaxableAmt, tax, CGST, SGST, IGST |
| **Inward Supplies** | (Similar structure for reverse charge) |
| **ITC** | Inter, Intera (ITC available) |
| **Fees** | CessAmt, fee (late fees) |
| **Location** | POS |

#### Data Analysis

- **Total Records:** 37 (sparse data - mostly summary rows)
- **Columns:** Only TaxableAmt and CessAmt show meaningful data
- **Purpose:** Monthly GSTR-3B return filing summary

**Note:** This table appears to store summarized GSTR-3B data for specific sections only. Most columns are unused.

---

## Empty Tables (Structure Only)

### 1. GSTInfo (0 rows, 44 columns)

**Purpose:** GST payment challan and liability tracking

#### Key Columns

| Category | Columns |
|----------|---------|
| **Payment** | Date, Amount, ChallanNo, ChallanDate, ChequeNo, ChequeDate |
| **Bank** | BankName, BankCode, BankAcType, BankAcNo |
| **Tax Rates** | CGSTPercent, SGSTPercent, IGSTPercent, CessPercent, ACessPercent |
| **Tax Amounts** | CGSTAmt, SGSTAmt, IGSTAmt, CessAmt, ACessAmt |
| **Fees** | Interest, Penalty, LateFee |
| **Custom** | D1-D15 (15 custom data fields) |

**Business Use:** Track GST payments made to government, interest, penalties, and late fees.

---

### 2. GSTR1Info (0 rows, 63 columns)

**Purpose:** GSTR-1 return filing data (outward supplies)

#### Key Columns

| Category | Columns |
|----------|---------|
| **Identity** | RecType, TranType, Month, Year, SrNo, GSTIN, CompGSTIN |
| **Invoice** | Date, VchNo, CrDate, CrNo, InvType, TotalAmt, TaxableAmt |
| **Tax** | Rate, CGST, SGST, IGST, CessAmt |
| **Location** | POS, cfs (counter-party filing status) |
| **HSN** | hsnsc, Desc, uqc, qty |
| **Party** | cName, pGST |
| **Doc Series** | Docfrom, DocTo, netissue, docnum |
| **Filing** | filDate, filType, ReportType |

**Business Use:** Store GSTR-1 return data for outward supplies reporting.

---

### 3. VATInfo (0 rows, 22 columns)

**Purpose:** VAT (pre-GST era) tax tracking

**Note:** This table is obsolete for current GST regime but retained for historical data.

---

## Data Relationships and Linkages

### Transaction Tax Flow

```
Transaction (VchMaster)
    ↓
VchGSTSumItemWise (Item-level tax details)
    ↓
GSTR1Info/GSTR2AInfo/GSTR2BInfo (Return filing data)
    ↓
GSTR3BInfo (Monthly summary)
    ↓
GSTInfo (Payment tracking)
```

### Key Joins

1. **Transaction to Tax Details:**
   ```sql
   VchMaster.VchCode = VchGSTSumItemWise.VchCode
   ```

2. **Transaction to Party:**
   ```sql
   VchGSTSumItemWise.PartyCode = MasterMaster.Code
   ```

3. **Transaction to Item:**
   ```sql
   VchGSTSumItemWise.ItemCode = ItemMaster.Code
   ```

4. **GSTR2A/B to Transaction:**
   ```sql
   GSTR2AInfo.VchNo = VchMaster.VchNo (approximate)
   ```

---

## Tax Amount Breakdown Summary

### VchGSTSumItemWise (Primary Transaction Data)

| Tax Component | Total Amount (₹) |
|---------------|------------------|
| Taxable Amount | 306,476,041.19 |
| **Note:** Tax amounts stored as TaxAmt/TaxAmt1 (CGST/SGST split) |

### GSTR2AInfo (Auto-Populated Purchase Data)

| Tax Component | Total Amount (₹) |
|---------------|------------------|
| Total Amount | 124,129,993.40 |
| Taxable Value | 116,888,120.78 |
| CGST | 2,046,278.74 |
| SGST | 2,046,278.74 |
| IGST | 3,150,080.04 |
| **Total Tax** | **7,242,637.52** |

### GSTR2BInfo (ITC Statement)

| Tax Component | Total Amount (₹) |
|---------------|------------------|
| Total Amount | 151,647,103.56 |
| Taxable Value | 143,045,493.77 |
| CGST | 2,378,295.71 |
| SGST | 2,378,295.71 |
| IGST | 3,851,256.31 |
| **Total Tax** | **8,607,847.73** |

---

## Recommendations for Complete Ledger with Tax Details

### 1. For Transaction-Level Tax Details

**Use:** `VchGSTSumItemWise`

**Join Query:**
```sql
SELECT 
    vm.VchCode,
    vm.VchNo,
    vm.VchDate,
    vm.VchType,
    mm.Name AS PartyName,
    mm.GSTNo,
    vgsi.HSNCode,
    vgsi.TaxableAmt,
    vgsi.TaxRate + vgsi.TaxRate1 AS GSTRate,
    vgsi.TaxAmt + vgsi.TaxAmt1 AS TotalTax,
    vgsi.GSTR2BStatus,
    vgsi.ITCClaimedStatus
FROM VchMaster vm
INNER JOIN VchGSTSumItemWise vgsi ON vm.VchCode = vgsi.VchCode
LEFT JOIN MasterMaster mm ON vgsi.PartyCode = mm.Code
ORDER BY vm.VchDate DESC;
```

### 2. For ITC Reconciliation

**Use:** `GSTR2BInfo` (primary) or `GSTR2AInfo` (secondary)

**Key Fields:**
- GSTIN (supplier GST number)
- VchNo (invoice number)
- TaxableAmt, CGST, SGST, IGST (tax amounts)
- ITCAvl (ITC availability flag)

### 3. For GST Payment Tracking

**Use:** `GSTInfo` (when populated)

**Note:** Currently empty - may need manual entry or import from GST portal.

### 4. For GSTR-1 Reporting

**Use:** `GSTR1Info` (when populated) or derive from `VchGSTSumItemWise`

---

## Important Notes

### Data Quality Observations

1. **VchGSTSumItemWise:**
   - Contains comprehensive item-level tax data
   - GSTR2B integration fields mostly empty (0 values)
   - ITC tracking fields need population

2. **GSTR2A vs GSTR2B:**
   - GSTR2B has more records (3,650 vs 3,101)
   - GSTR2B amounts are higher (indicates more recent data)
   - GSTR2B includes TradeName field

3. **GSTR3BInfo:**
   - Very sparse data (only 37 rows)
   - Most tax columns empty
   - May require data import from GST portal

4. **Empty Tables:**
   - GSTInfo, GSTR1Info, VATInfo have structure but no data
   - May be populated during specific operations only

### Technical Notes

- **Company GSTIN:** 06AKOPG5313N1ZX (Haryana)
- **State Code:** 06 (Haryana)
- **POS 0:** Intra-state transactions
- **POS 6:** Inter-state transactions
- **Date format:** Access datetime
- **Amount precision:** Float (53-bit)

---

## Conclusion

For a complete ledger with tax details, the primary table is **VchGSTSumItemWise** which contains:

- Item-level tax calculations
- HSN codes
- Transaction linking (VchCode)
- Party linking (PartyCode)
- GSTR2B reconciliation fields
- State/location information

For ITC tracking and reconciliation, use **GSTR2BInfo** as the primary source with **GSTR2AInfo** as a cross-reference.

The empty tables (GSTInfo, GSTR1Info) may require manual data entry or GST portal integration to populate.

---

## Appendix: Column Counts Summary

| Table | Columns | Rows | Status |
|-------|---------|------|--------|
| GSTInfo | 44 | 0 | Empty |
| GSTR1Info | 63 | 0 | Empty |
| GSTR2AInfo | 54 | 3,101 | Active |
| GSTR2BInfo | 54 | 3,650 | Active |
| GSTR3BInfo | 33 | 37 | Sparse |
| VATInfo | 22 | 0 | Empty |
| VchGSTSumItemWise | 52 | 26,159 | Active |

---

*Report generated using 32-bit Python with MS Access ODBC connectivity*
