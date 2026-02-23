# Item Master Tables Analysis

**Database:** C:\Users\Vibhor\Desktop\COMP0012\db12025.bds  
**Analysis Date:** 2026-02-23  
**Analyzed Tables:** ItemDesc, ItemSerialNo, Master1 (MasterType 6)

---

## Executive Summary

The database does not have a traditional "Item Master" table named "ItemDesc" or "ItemSerialNo". Instead:

- **Actual Item Master:** `Master1` table where `MasterType = 6` (4,394 items)
- **Item Groups:** `Master1` table where `MasterType = 5` (33 groups)
- **ItemDesc:** Voucher description lines (NOT item master) - 10,689 rows
- **ItemSerialNo:** Serial number tracking table (currently empty) - 0 rows

---

## 1. Master1 Table - Item Master (MasterType = 6)

### Overview
- **Total Items:** 4,394
- **MasterType:** 6 (identifies items vs other master types)
- **Primary Key:** `Code`

### Column Structure (156 columns)

Key columns for item management:

| Column | Type | Description |
|--------|------|-------------|
| `Code` | Integer | Unique item code (Primary Key) |
| `MasterType` | Integer | Always 6 for items |
| `Name` | String (40) | Item name |
| `Alias` | String (40) | Item alias/code (often used for item codes) |
| `PrintName` | String (60) | Name to print on documents |
| `ParentGrp` | Integer | Reference to item group (Master1.Code where MasterType=5) |
| `HSNCode` | String | HSN/SAC code for GST |

Configuration columns (CM1-CM11, D1-D26, I1-I30):
- Custom fields for item attributes
- Used for various item-specific configurations
- Example: `Alias` field often contains SKU codes like "078008821000"

Tracking columns:
- `CreatedBy`, `CreationTime`
- `ModifiedBy`, `ModificationTime`
- `BlockedMaster`, `DeactiveMaster`

### Sample Items

```
Code 23749: BLOCK & BLOOM KING BEDSHEET
  Alias: 078008821000
  Print: BLOCK & BLOOM KING BEDSHEET
  Parent: 23743 (BED SHEET group)

Code 23759: KATREENA DELIGHT D/B BEDSHEET
  Alias: 07508800980
  Print: KATREENA DELIGHT D/B BEDSHEET
  Parent: 23743 (BED SHEET group)

Code 23783: HAMILTON D/B COMF.
  Alias: A006.0007
  Print: HAMILTON D/B COMF.
  Parent: 23745 (COMFORTER 12% group)
```

### Item Groups (MasterType = 5)

33 unique groups identified:

| Group Code | Group Name |
|------------|------------|
| 401 | GENERAL |
| 23743 | BED SHEET |
| 23744 | HANDICRAFT |
| 23745 | COMFORTER 12% |
| 23746 | COMFORTER 18% |
| 23747 | BLANKET |
| 23748 | TOP SHEET / DOHAR |
| 23841 | TOWEL |
| 24010 | BEDCOVER |
| 24367 | CLOTH |

**Hierarchy:** Items → Item Groups via `ParentGrp` field

---

## 2. ItemDesc Table - Voucher Descriptions

### Overview
- **Total Rows:** 10,689
- **Purpose:** Multi-line descriptions for vouchers
- **Misconception:** NOT an item master table

### Column Structure (30 columns)

| Column | Type | Description |
|--------|------|-------------|
| `VchCode` | Integer | Voucher reference (links to Tran1) |
| `SrNo` | Integer | Serial number within voucher |
| `Desc1` - `Desc20` | String | Description lines 1-20 |
| `D1`, `D2`, `D3` | Float | Numeric values |
| `I1` | Integer | Integer value |
| `Desc1SL` - `Desc4SL` | String | Additional description lines |

### Sample Data

```
VchCode: 14005, SrNo: 1
  Desc1: RAINBOW

VchCode: 14014, SrNo: 1
  Desc1: LITTLE PALM BABY

VchCode: 14014, SrNo: 2
  Desc1: TEDDY TOY
```

**Usage:** Used for adding descriptive text to vouchers, not for storing item definitions.

---

## 3. ItemSerialNo Table - Serial Number Tracking

### Overview
- **Total Rows:** 0 (empty table)
- **Purpose:** Track individual item serial numbers

### Column Structure (28 columns)

| Column | Type | Description |
|--------|------|-------------|
| `VchCode` | Integer | Voucher reference |
| `VchType` | Integer | Voucher type |
| `VchNo` | String | Voucher number |
| `ItemCode` | Integer | Item code (Master1.Code) |
| `SerialNo` | String | Individual serial number |
| `WarrantyMonth` | Integer | Warranty period in months |
| `Date` | DateTime | Transaction date |
| `Value1`, `Value2` | Float | Values (cost, MRP, etc.) |

### Purpose (when used)

This table would track:
- Individual serialized items (electronics, appliances)
- Warranty information
- Item history across transactions
- Currently not in use (0 rows)

---

## 4. Transaction Linkages

### How Items Connect to Transactions

```
┌─────────────────┐      ┌─────────────┐      ┌─────────────────┐
│   Master1       │      │    Tran2    │      │     Tran1       │
│ (MasterType=6)  │◄─────│ MasterCode1 │─────►│   VchCode       │
│   Items         │      │  Item Line  │      │   Voucher       │
└─────────────────┘      └─────────────┘      └─────────────────┘
                               │
                               │ MasterCode2
                               ▼
                        ┌─────────────┐
                        │   Master1   │
                        │ (Ledger/    │
                        │  Account)   │
                        └─────────────┘
```

### Tran2 Table (Item Transaction Details)

- **Total Rows:** 88,717 transaction lines
- **Key Columns:**
  - `VchCode`: Voucher identifier
  - `MasterCode1`: Item code (Master1.Code, MasterType=6)
  - `MasterCode2`: Account/Ledger code (Master1.Code, other MasterTypes)

### ItemDesc Linkage

```
Tran1.VchCode ──────► ItemDesc.VchCode
                            │
                            ├─ SrNo: 1 (Desc1: Item description)
                            ├─ SrNo: 2 (Desc1: Additional details)
                            └─ ...
```

---

## 5. MasterType Reference

Complete list of MasterTypes found in database:

| MasterType | Count | Description |
|------------|-------|-------------|
| 1 | 54 | General Ledger Accounts |
| 2 | 8,031 | Parties/Customers/Suppliers |
| 3 | 1 | Other masters |
| 5 | 33 | Item Groups |
| **6** | **4,394** | **Items/Products** |
| 7 | 3 | Currencies |
| 8 | 12 | Units of Measure |
| 9 | 43 | Voucher Types/Auto-Vouchers |
| 10 | 4 | Godown Types |
| 11 | 3 | Godowns |
| 12 | 8 | Tax Categories |
| 13 | 24 | Local GST Configs |
| 14 | 43 | Interstate GST Configs |
| 16 | 3 | Unit Combinations |
| 19 | 3 | Employee Masters |
| 21 | 31 | Branch Masters |
| 22 | 14 | TDS Categories |
| 25 | 9 | GST Tax Classes |
| 27 | 2 | Salesmen |
| 28 | 2 | Cost Centers |
| 29 | 6 | Salary Heads |
| 30 | 13 | Discount Schemes |
| 31 | 13 | Markup Schemes |
| 55 | 20 | Countries |
| 56 | 42 | States |
| 60 | 7 | Departments |

---

## 6. Stock/Inventory Implications

### Stock Tracking

Items have stock tracking through:

1. **Tran2 table:** Records all item movements
   - Purchases (inward)
   - Sales (outward)
   - Stock transfers
   - Adjustments

2. **Balance fields in Tran2:**
   - `Balance1`, `Balance2`, `Balance3`: Running balances
   - `ItemBal1`, `ItemBal2`, `ItemBal3`: Item-specific balances

### Unit of Measure

- Units stored in MasterType 8
- Examples: Pcs, Kgs., GMS., UNITS
- Multi-unit items use MasterType 16 (Unit Combinations)

### Pricing

- Item master doesn't store fixed prices
- Prices determined at transaction time
- Can use pricing schemes (MasterTypes 30, 31)

---

## 7. Query Examples

### Get All Items
```sql
SELECT Code, Name, Alias, PrintName, ParentGrp
FROM Master1
WHERE MasterType = 6
ORDER BY Name
```

### Get Items by Group
```sql
SELECT i.Code, i.Name, i.Alias, g.Name as GroupName
FROM Master1 i
INNER JOIN Master1 g ON i.ParentGrp = g.Code
WHERE i.MasterType = 6
AND g.MasterType = 5
AND g.Name = 'BED SHEET'
```

### Get Item Transaction History
```sql
SELECT t.Date, t.VchNo, t.VchType, m.Name as ItemName, t.Qty, t.Rate
FROM Tran2 t
INNER JOIN Master1 m ON t.MasterCode1 = m.Code
WHERE m.MasterType = 6
AND m.Name LIKE '%BEDSHEET%'
ORDER BY t.Date DESC
```

### Get Item Descriptions from Vouchers
```sql
SELECT t.VchCode, t.VchNo, id.Desc1, id.Desc2
FROM Tran1 t
INNER JOIN ItemDesc id ON t.VchCode = id.VchCode
WHERE t.VchCode = 14014
```

---

## 8. Key Insights

1. **Item Master Location:** Items are in `Master1` with `MasterType = 6`, not in `ItemDesc`

2. **Flexible Structure:** Master1 uses a generic structure with many custom fields (CM, D, I columns)

3. **Item Codes:** Often stored in `Alias` field (alphanumeric codes like "078008821000", "A006.0007")

4. **No Serial Tracking:** ItemSerialNo table exists but is empty (not used currently)

5. **Hierarchical:** Items grouped under categories via `ParentGrp` field

6. **Transaction-Driven:** Stock quantities derived from Tran2 records, not stored in item master

7. **HSN Support:** Dedicated `HSNCode` column for GST compliance

---

## 9. Integration Recommendations

For Busy Whatsapp Bridge integration:

1. **Item Lookup:** Query Master1 WHERE MasterType = 6
2. **Item Search:** Search by Name, Alias, or PrintName
3. **Stock Query:** Join Tran2 to get current stock levels
4. **Group Filter:** Filter by ParentGrp for category-specific queries
5. **Descriptions:** Use ItemDesc for voucher-level descriptions, not item details

---

*Analysis completed using 32-bit Python with pyodbc*
