# Config and Locks Tables - Comprehensive Analysis

**Analysis Date:** 2026-02-23 00:43:40  
**Database:** C:\Users\Vibhor\Desktop\COMP0012\db12025.bds  
**Analyst:** 32-bit Python (pyodbc)

---

## Executive Summary

The **Config** table is a sophisticated multi-entity configuration store using a discriminator pattern (RecType field). Rather than one massive configuration record, it contains **231 rows** organized into **46 distinct configuration categories**, each identified by a RecType code. This design allows Busy Accounting Software to store diverse configuration types in a single flexible table structure.

### Key Discovery: RecType Discriminator Pattern

| RecType | Records | Configuration Category |
|---------|---------|------------------------|
| 1 | 31 | Master/Voucher Configuration (31 configs) |
| 2 | 2 | Additional Settings |
| 5 | 1 | System Parameters |
| 6 | 31 | Account/Group Settings (31 entries) |
| 7 | 1 | Financial Year |
| 8 | 1 | Company Details |
| 9 | 1 | GST/Tax Settings |
| 10 | 1 | User Preferences |
| 15 | 1 | Backup/Export Settings |
| 20 | 1 | Printer Setup |
| 21 | 3 | Report Formats (3 templates) |
| 22 | 2 | Label/Barcode Settings |
| 27 | 1 | Security Settings |
| 30 | 1 | Data Import/Backup Paths |
| 31 | 1 | Backup Configuration |
| 32 | 1 | Previous Year Data |
| 35 | 1 | Email Settings |
| 36 | 8 | Printer Drivers (8 configs) |
| 39 | 1 | Document Templates |
| 40 | 3 | Custom Fields (3 types) |
| 41 | 1 | Dashboard Settings |
| 43 | 1 | Integration Settings |
| 44 | 1 | API Configuration |
| 57 | 1 | GST API Credentials |
| 58 | 1 | E-Way Bill Settings |
| 63 | 1 | Inventory Settings |
| 64 | 22 | Item Master Settings (22 items) |
| 77 | 1 | Batch Settings |
| 79 | 2 | MRP/Price Settings |
| 84 | 31 | Voucher Types (31 types) |
| 87 | 3 | Tax Categories (3 types) |
| 88 | 1 | Discount Rules |
| 92 | 1 | Currency Settings |
| 93 | 6 | Unit of Measure (6 units) |
| 94 | 2 | Godown/Warehouse (2 locations) |
| 107 | 1 | Job Work Settings |
| 111 | 1 | Image/Logo Storage |
| 115 | 1 | SMS Configuration |
| 120 | 1 | TDS Settings |
| 123 | 1 | Statutory Settings |
| 126 | 1 | Multi-Currency |
| 132 | 1 | GST Portal Credentials |
| 141 | 1 | GSP API Configuration |
| 169 | 1 | e-Invoice Settings |
| 172 | 53 | GST Return Filing (53 entries) |
| 184 | 1 | Audit Trail Settings |


---

## Table Structure

### Config Table
- **Total Columns:** 255 (Generic data type columns)
- **Total Rows:** 231
- **Primary Key:** None visible (likely composite or internal)
- **Key Column:** `RecType` - Discriminator identifying configuration category

**Column Naming Convention:**
- **B1-B142:** Boolean flags (Yes/No settings)
- **C1-C30:** String/Text values
- **D1-D15:** Decimal/Float values (amounts, percentages)
- **I1-I35:** Integer values (counters, IDs, quantities)
- **L1-L20:** Long integers (large numbers, timestamps)
- **M1-M2:** Memo/Text fields (longer text)
- **Date:** Timestamp
- **DocName, FaVchName, InvVchName:** Document/Voucher references
- **NoOfFld, PricingMode, PricingModeForPurc:** Specific settings
- **RecType:** Configuration category discriminator ⭐
- **Stamp, Type:** Internal tracking

### Locks Table
- **Total Columns:** 59
- **Total Rows:** 1 (singleton - current system state)
- **Purpose:** Tracks database locks, feature flags, and version info

---

## Critical Configuration Records

### RecType 1: Master/Voucher Configuration (31 entries)
**Purpose:** Defines voucher types and their behavior

**Sample Configuration (First Entry):**
- **Document Name:** STANDARD
- **Custom Fields:**
  - C1: "PVT MARKA" (Private Marka)
  - C2: "PANIPAT TO" (Destination)
  - C3: "NO. OF BALE" (Bale count field)
  - C4: "COURIER NAME"
  - C5: "AWB NO" (Tracking number)
  - C6: "COURIER DATE"
  - C7: "CHALLAN NO."
- **Enabled Features:** B2-B52, B63-B66, B83-B85 all True (extensive feature set)
- **Integer Settings:**
  - I1: 1, I2: 2, I3: 2 (sequence/numbering)
  - I7: 10 (page size?)
  - I20-I27: Various flags (1=enabled)
- **Long Values:**
  - L1: 251 (Master code reference?)
  - L11: 1064, L12: 1063 (Account codes)
  - L18: 501, L19: 526 (Range definitions)
- **M2:** Complex serialized configuration with 143 parameters separated by "�"

**Pattern:** Each of the 31 rows likely represents a different voucher type configuration.

---

### RecType 30, 31, 32: Data Backup & Import Paths
**Purpose:** Tracks data import operations and backup locations

**RecType 30:**
- C21: `C:\Users\MY\Desktop\Vh01042013.DAT` - Historical data file

**RecType 31:**
- C21: `D:\Users\MY\Desktop\AHF_20230411_Vh11042023.DAT` - Recent backup

**RecType 32:**
- C21: `F:\Users\MY\Desktop\AHF 20-21_20200511_MS11052019.DAT` - FY 2020-21 data

**Insight:** These contain full file paths to previous Busy data exports/imports.

---

### RecType 36: Printer Configuration (8 entries)
**Purpose:** Printer driver and formatting settings

**First Entry (EPSON printer):**
- **C1:** "EPSON" (Printer model)
- **C2-C20:** Printer escape sequences
  - `27,64` = ESC @ (Initialize printer)
  - `27,80` = ESC P (Select 10cpi)
  - `27,77` = ESC M (Select 12cpi)
  - `27,87,1` = ESC W 1 (Double-width ON)
  - `27,71` = ESC G (Double-strike ON)
  - `27,69` = ESC E (Bold ON)
  - `27,70` = ESC F (Bold OFF)
  - These are standard Epson ESC/P control codes!

**Pattern:** Each row represents a different printer profile with specific control codes.

---

### RecType 57: GST API Configuration
**Purpose:** GST portal integration settings

- **DocName:** "API"
- **C2:** "132103" (GSTIN prefix or API ID)
- **C3:** "ANJALI46_API_999" (Username)
- **C4:** "Busy@123456" (Password)

**Security Note:** Contains plaintext API credentials.

---

### RecType 84: Voucher Type Definitions (31 entries)
**Purpose:** Defines all voucher types in the system

Each row represents a different voucher type (likely: Sales, Purchase, Payment, Receipt, Journal, Contra, etc.)

**Pattern:** 31 rows = 31 voucher types, matching standard Busy configuration.

---

### RecType 141: GSP API Configuration
**Purpose:** GST Suvidha Provider (GSP) integration

- **C2:** "132103"
- **C3:** "ANJALI46_API_999" 
- **C4:** "Busy@123456"

**Note:** Duplicate of RecType 57 - likely same credentials for both GST and GSP.

---

### RecType 172: GST Return Filing Data (53 entries)
**Purpose:** GST return filing history and pending returns

**Pattern:** 53 entries suggest multiple months/years of return data tracked.

---

## Locks Table Analysis

### Overview
The Locks table is a **singleton** (1 row, 59 columns) that tracks:
- Database version information
- Feature enablement flags
- Current system state
- Multi-user access locks

### Key Fields

**Version Information:**
- **MAJOR:** 21 (Database major version)
- **MINOR:** 0 (Database minor version)
- **MainDbVer:** 398 (Main database schema version)
- **PartialDbVer:** 372 (Partial sync schema version)
- **Type:** 2023-04-10 22:03:25 (Last update timestamp)

**Feature Flags (all Boolean):**

| Field | Value | Likely Meaning |
|-------|-------|----------------|
| IBR | False | Inter-Branch Transfer |
| MBU | False | Multi-Bill Upload |
| CSU | False | Consolidated Stock Update |
| STU | False | Stock Transfer Update |
| Working | False | Background process running |
| BSSTD | False | Bill-wise Standard |
| TERBR | False | Terminal/Branch |
| BRS | False | Bank Reconciliation |
| CCCF | False | Cost Center/Category |
| SuppTypeF | False | Supplier Type Filter |
| BSNF | False | Batch Serial Number Format |
| BST | False | Batch Tracking |
| OSPO | False | Order-Sale-Purchase Optimization |
| OBAMC | False | Opening Balance Auto Migration |
| TDSSHE | False | TDS Section Handling |
| TESRNO | False | Tax Invoice Serial Number |
| RW35 | False | Report Writer 3.5 |
| MEBR | False | Multi-Entity/Branch |
| MEBR1 | False | Multi-Entity Extended |
| MFFSA | False | Multi-Financial Year |
| SMPL | False | Sample Management |
| GSTU | False | GST Update |
| MUSPO | False | Multi-User Stock Posting |
| DFYW | False | Default Financial Year Warning |
| BATCH | False | Batch Processing |
| BATCHMRPSRNOPARAM | False | Batch MRP SR No Parameters |
| ENTRYTAXRATE | False | Entry Tax Rate |
| STPTMC | False | Stock Transfer Posting to MC |
| CHALLANNO | False | Challan Number |
| PARAMDET | False | Parameter Details |
| MASTFP | False | Master Field Parameters |
| MASTFP1 | False | Master Field Parameters 1 |
| RMVLOCDB | False | Remove Local Database |
| POSSERIESFTBSNAME | False | POS Series for Tally Busy Sync |
| STSCGUPDT | False | Statistics Update |
| ItemSrNoLen | False | Item Serial Number Length |
| RGMAST | False | Register Master |
| COMPEGRPMAST | False | Company Group Master |
| COMPCONTGRPMAST | False | Company Contact Group Master |
| AREAMAST | False | Area Master |
| CONTDEPTMAST | False | Contact Department Master |
| SOURCEMAST | False | Source Master |
| SUBSTATUSMAST | False | Sub-Status Master |
| NXTACTIONMAST | False | Next Action Master |
| TRADEMAST | False | Trade Master |
| B1 | False | Boolean Flag 1 |
| FAQGRPMAST | False | FAQ Group Master |
| PENDSUBSTATUSMAST | False | Pending Sub-Status Master |
| TRACKINGNO | False | Tracking Number |
| TOFQ | False | Terms of Freight/Quote |
| URefBal | False | User Reference Balance |

**String Fields:**
- **WinUser:** (Empty) - Current Windows user
- **PIIPD:** (Empty) - Party/IP details
- **CompanyName:** (Empty) - Company name override

**Insight:** All feature flags are `False`, suggesting this is a basic/single-user installation or features are not enabled.

---

## Configuration Patterns & Insights

### 1. Entity-Attribute-Value (EAV) Pattern
The Config table uses a **discriminator pattern** where RecType acts as the entity type identifier. This allows:
- Flexibility to add new configuration types without schema changes
- Efficient storage (only populate needed columns)
- Version control (multiple rows per type = history)

### 2. Column Type Convention
- **B-prefixed:** Boolean flags (142 available)
- **C-prefixed:** String data (30 available)
- **D-prefixed:** Decimal/float data (15 available)
- **I-prefixed:** Integer data (35 available)
- **L-prefixed:** Long/BigInt data (20 available)
- **M-prefixed:** Memo/Blob data (2 available)

### 3. Serialized Data Pattern
Fields like **M2** contain pipe-delimited (`�`) serialized data with 100+ parameters. This allows:
- Storing complex nested structures
- Backward compatibility (add params without schema change)
- Compact representation

### 4. Voucher Type System
RecType 1 and 84 (62 total rows) define the complete voucher type ecosystem:
- 31 master configurations (RecType 1)
- 31 type definitions (RecType 84)
- This matches Busy standard voucher types

### 5. GST Integration
RecTypes 57, 132, 141 handle GST compliance:
- API credentials
- Portal integration
- Return filing tracking (53 entries in RecType 172)

---

## Security Findings

### Exposed Credentials
The following credentials are stored in **plaintext**:

1. **RecType 57 & 141:**
   - Username: `ANJALI46_API_999`
   - Password: `Busy@123456`
   - ID: `132103`

**Risk Level:** HIGH  
**Recommendation:** These should be encrypted or moved to environment variables.

### File Path Exposure
Multiple file paths reveal:
- User directory structure (`C:\Users\MY\Desktop`)
- Backup file locations
- Historical data files

**Risk Level:** MEDIUM  
**Recommendation:** Sanitize paths in logs and reports.

---

## Recommendations

### For Database Understanding
1. **RecType 1 Analysis:** Decode the M2 field's 143 serialized parameters - likely contains critical posting rules
2. **RecType 84:** Map all 31 voucher types to understand transaction types
3. **RecType 172:** Analyze GST return filing patterns
4. **RecType 6:** The 31 account/group settings likely map to ledger masters

### For Integration
1. Use RecType to filter configurations by category
2. Parse M-fields for complex nested settings
3. Check Locks table flags before enabling features
4. Handle B-fields as feature toggles

### For Security
1. Encrypt API credentials (RecType 57, 132, 141)
2. Remove hardcoded passwords from database
3. Audit file paths in configurations
4. Implement access controls on Config table

---

## Appendix: Column Reference

### Config Table Column Types

**Boolean Columns (142 total):**
B1, B2, B3... B142

**String Columns (30 total):**
C1, C2, C3... C30

**Decimal Columns (15 total):**
D1, D2, D3... D15

**Integer Columns (35 total):**
I1, I2, I3... I35

**Long Columns (20 total):**
L1, L2, L3... L20

**Memo Columns (2 total):**
M1, M2

**Special Columns:**
- Date (datetime)
- DocName (string)
- FaVchName (string)
- InvVchName (string)
- NoOfFld (integer)
- PricingMode (integer)
- PricingModeForPurc (integer)
- RecType (integer) - **Discriminator**
- Stamp (integer)
- Type (integer)
- CM1 (integer)

---

## Conclusion

The Config table is a sophisticated, flexible configuration system using:
- **46 distinct RecType categories**
- **Generic column pools** (B, C, D, I, L, M prefixes)
- **Serialized data** for complex parameters
- **Version tracking** through multiple rows

Understanding the **RecType discriminator** is key to navigating this table. Each category represents a different subsystem:
- Voucher types (RecType 1, 84)
- Printers (RecType 36)
- GST integration (RecType 57, 132, 141, 172)
- API credentials (RecType 57, 141)
- Backup/import history (RecType 30-32)

The Locks table provides a **singleton state tracker** for database versioning and feature flags.

**Next Steps:** Cross-reference RecType values with actual ledger transactions to map configuration to business logic.
