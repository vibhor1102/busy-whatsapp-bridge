# Help1 and Help2 Tables Analysis

## Overview

| Table | Columns | Rows | Purpose |
|-------|---------|------|---------|
| Help1 | 14 | 56,435 | Master lookup table with code-to-name mappings |
| Help2 | 4 | 20,498 | Item/Voucher cross-reference lookup |

---

## Help1 Table Structure

| Column | Type | Purpose |
|--------|------|---------|
| RecType | int | Record type classification |
| NameAlias | string(255) | Name or alias text |
| Code | int | **Primary code/key** for the record |
| MasterType | int | **Master type classification** (38 types) |
| NameOrAlias | int | Flag: 1=Name, 2=Alias |
| AdditionalInfo | string(255) | Additional details/address |
| ParentGroup | int | Parent group code |
| MasterSeries | int | Series grouping |
| Status | int | 0=Active |
| DefaultMCCode | int | Default master code |
| AddnInfoBt1-4 | various | Additional boolean/info fields |

---

## MasterType Codes (Help1)

| Code | Count | Description |
|------|-------|-------------|
| 1 | 220 | **Account Group Masters** - Chart of account groups |
| 2 | 48,648 | **Account Masters** - Party/ledger accounts |
| 3 | 1 | **GST Tax Masters** - Tax configurations |
| 5 | 33 | **Item Group Masters** - Product categories |
| 6 | 7,101 | **Item Masters** - Individual products/items |
| 7 | 3 | **Currency Masters** - Foreign currencies |
| 8 | 12 | **Unit Masters** - Measurement units (Pcs, Kg, etc.) |
| 9 | 44 | **Voucher Type Masters** - Discount, Rounding off, etc. |
| 10 | 4 | **Godown Category Masters** - Storage categories |
| 11 | 3 | **Godown Masters** - Specific storage locations |
| 12 | 8 | **Material Centre Category** |
| 13 | 48 | **Material Centre Masters** |
| 14 | 86 | **Cost Centre Category** |
| 21 | 31 | **Bill Sundry Masters** - Additional charges/discounts |
| 22 | 14 | **Tag Masters** |
| 25 | 9 | **Department Masters** |
| 27 | 6 | **Employee Category** |
| 28 | 2 | **Employee Masters** |
| 29 | 12 | **Location Masters** |
| 30 | 19 | **Salesman Masters** |
| 31 | 20 | **Route Masters** |
| 55-68 | 99 | **Custom Master Types** |
| 1008 | 11 | **Special/System Types** |

### Key MasterType Mappings:

```
MasterType 1  → Account Groups (Capital Account, Current Assets, etc.)
MasterType 2  → Accounts/Parties (Customers, Suppliers, Banks)
MasterType 5  → Item Groups (BED SHEET, HANDICRAFT, GENERAL)
MasterType 6  → Items/Products (MILLI (BOX) SIG, LILAC 1+2 BOX BEDSHEET)
MasterType 8  → Units (N.A., Pcs, UNITS)
MasterType 9  → Voucher Types (DISCOUNT, Rounded Off)
MasterType 11 → Godowns (Main Store, VIBHOR AHD CREATION)
```

---

## RecType Codes (Help1)

| Code | MasterType | Count | Description |
|------|------------|-------|-------------|
| 1 | 2 | 8,227 | **Account Master Names** |
| 2 | 1 | 55 | **Account Group Names** |
| 3 | 6 | 7,101 | **Item Master Names** |
| 4 | 5 | 33 | **Item Group Names** |
| 6 | 3 | 1 | **GST Tax Name** |
| 7 | 8 | 12 | **Unit Names** |
| 8 | 7 | 3 | **Currency Names** |
| 9 | 9 | 44 | **Voucher Type Names** |
| 10 | 11 | 3 | **Godown Names** |
| 11 | 12 | 8 | **Material Centre Category Names** |
| 12 | 13 | 24 | **Material Centre Names** |
| 13 | 14 | 43 | **Cost Centre Category Names** |
| 14 | 10 | 4 | **Godown Category Names** |
| 15 | 19 | 3 | Unknown |
| 18 | 21 | 31 | **Bill Sundry Names** |
| 19 | 22 | 14 | **Tag Names** |
| 21 | 28 | 2 | Unknown |
| 22 | 27 | 6 | **Employee Category Names** |
| 23 | 29 | 12 | **Location Names** |
| 24 | 30 | 13 | **Salesman Names** |
| 25 | 31 | 20 | **Route Names** |
| 55-73 | Various | 91 | **Custom Types** |
| 101 | 2 | 8 | **Account Alternate Names** |
| 102 | 2 | 8,218 | **Account Mobile Numbers** |
| 103 | 2 | 7,898 | **Account Phone Numbers** |
| 104 | 2 | 7,906 | **Account Contact Numbers** |
| 105 | 2 | 52 | **Account Email** |
| 106 | 2 | 158 | **Account Address** |
| 107 | 2 | 8,226 | **Account Party Names (Alternate)** |
| 108 | 2 | 6 | **Account GST Numbers** |
| 109 | 2 | 32 | **Account PAN Numbers** |
| 110 | 2 | 1 | Unknown |
| 111 | 2 | 7,916 | **Account Additional Info** |
| 151 | 13 | 1 | Unknown |
| 152 | 13 | 23 | Unknown |
| 153 | 14 | 1 | Unknown |
| 154 | 14 | 42 | Unknown |
| 201-206 | 1 | 125 | **Account Group Alternate/Reporting Names** |
| 501 | 30 | 6 | Unknown |
| 502 | 31 | 7 | Unknown |
| 512 | 27 | 3 | Unknown |
| 1008 | 1008 | 11 | **System/System-defined Types** |

---

## Status Codes (Help1)

| Code | Count | Meaning |
|------|-------|---------|
| 0 | 56,435 | **ACTIVE** - All records are active |

**Note:** No inactive/deleted records found in Help1. Status 1 would indicate deleted.

---

## NameOrAlias Codes (Help1)

| Code | Count | Meaning |
|------|-------|---------|
| 1 | 52,543 | **NAME** - Primary name of the master |
| 2 | 3,892 | **ALIAS** - Alternate name/code/identifier |

---

## Code-to-Name Mapping Examples

### Account Groups (MasterType=1)
```
Code 101: Capital Account
Code 102: Loans (Liability)
Code 103: Current Liabilities
Code 104: Fixed Assets
Code 105: Investments
Code 106: Current Assets
Code 107: Branch/Divisions
Code 108: Misc. Expenses (ASSET)
Code 109: Suspense A/c
Code 110: Reserves & Surplus
Code 111: Bank Accounts
Code 112: Cash-in-Hand
Code 113: Deposits (Asset)
Code 114: Loans & Advances (Asset)
Code 115: Stock-in-Hand
Code 116: Sundry Debtors
Code 117: Sundry Creditors
```

### Account Masters (MasterType=2)
```
Code 34966: Party with mobile 9872980000 (ParentGroup=116 = Sundry Debtors)
Code 34968: AJS TRADERS & DEVELOPERS - KAPURTHALA
```

### Item Groups (MasterType=5)
```
Code 401: GENERAL
Code 23743: BED SHEET
Code 23744: HANDICRAFT
```

### Item Masters (MasterType=6)
```
Code 33604: MILLI (BOX) SIG / 500505500 (alias)
Code 30497: LILAC 1+2 BOX BEDSHEET (INDRA) / 750750750 (alias)
Code 32685: DESIRE D/B BEDSHEET (BELLA CASA) / 050005080500 (alias)
Code 28189: FORTUNE KING BEDSHEET (BELLA CASA) / 060006080600 (alias)
Code 32831: SIG MILLE D/B BEDSHEET / 050004790500 (alias)
```

### Units (MasterType=8)
```
Code 451: UNITS
Code 455: N.A.
Code 1054: Pcs
```

### Voucher Types (MasterType=9)
```
Code 27390: DISCOUNT
Code 1063: Rounded Off (+)
Code 1064: Rounded Off (-)
```

### Godowns (MasterType=11)
```
Code 201: Main Store
Code 28428: VIBHOR AHD CREATION
Code 28542: MEHAK GARDEN
```

---

## Help2 Table Structure

| Column | Type | Purpose |
|--------|------|---------|
| RecType1 | int | Primary record type |
| RecType2 | int | Secondary classification |
| RecType3 | int | Tertiary classification (appears to be Item Code) |
| Name | string(255) | Name/description |

---

## Help2 RecType Analysis

### RecType1 Distribution
```
RecType1 = 1: 20,498 rows (100%)
```

**RecType1 = 1** appears to be the only value, indicating this is the standard item/voucher reference table.

### RecType2 Distribution (94 unique values)
Key values:
```
RecType2 = 3:    460 rows
RecType2 = 4:    459 rows  
RecType2 = 7:  1,334 rows
RecType2 = 8:  1,403 rows
RecType2 = 9:  1,333 rows
RecType2 = 10: 1,530 rows
RecType2 = 11: 1,403 rows
RecType2 = 31: 9,158 rows (45% of data)
... (many more values)
```

**RecType2 appears to represent:**
- Different item categories or voucher types
- Value 31 dominates (9,158 records) - likely "Item Names" or primary product references
- Values 7-11 may represent different item attributes or alternate names

### RecType3 Distribution (1,997 unique values)
```
RecType3 ranges from 1 to ~3,500
Most common: 258 (5,785 rows), 259 (5,785 rows)
```

**RecType3 appears to be:**
- Item Code references (cross-referencing Help1.Code for MasterType=6)
- Values 258 and 259 are the most common - likely represent active/current item codes

---

## Help2 Examples by RecType2

### RecType2 = 31 (Item Names - 9,158 rows)
```
(1, 31, 258): 'Jarkan King'
(1, 31, 258): 'Bliss King108*108'
(1, 31, 258): 'Portico Elemental'
(1, 31, 258): 'Florida Rajai Cover'
(1, 31, 258): 'Cadbury Sale'
(1, 31, 258): 'Alexa Sale'
```

### RecType2 = 7 (Item Codes/Numbers - 1,334 rows)
```
(1, 7, 258): '1388'
(1, 7, 258): '1389'
(1, 7, 258): '1390'
(1, 7, 258): '1391'
(1, 7, 258): '1392'
(1, 7, 258): '1393'
```

### RecType2 = 3, 4, 8, 9, 10, 11
These appear to be other item attributes:
- Unit codes
- Barcode numbers
- Alternate names
- Group classifications

---

## Critical Code Mappings Summary

### MasterType to Entity Mapping
```
1   → Account Groups (Chart of Accounts)
2   → Accounts/Ledgers (Parties, Banks, Cash)
3   → Tax Masters
5   → Item Groups (Categories)
6   → Items/Products
7   → Currencies
8   → Units of Measurement
9   → Voucher Types (Discount, Rounding, etc.)
10  → Godown Categories
11  → Godowns/Locations
12  → Material Centre Categories
13  → Material Centres
14  → Cost Centre Categories
21  → Bill Sundry (Additional charges)
22  → Tags
25  → Departments
27  → Employee Categories
28  → Employees
29  → Locations
30  → Salesmen
31  → Routes
```

### RecType to Purpose Mapping (Help1)
```
1-25    → Primary master names (corresponds to MasterType 1-31)
55-73   → Custom user-defined types
101-111 → Account contact/info types (mobile, phone, email, address, GST, PAN)
201-206 → Account group alternate names
501-512 → Salesman/Route custom data
1008    → System reserved
```

### RecType to Purpose Mapping (Help2)
```
RecType1 = 1     → Standard reference record
RecType2 = 3-11  → Item attributes (codes, units, barcodes)
RecType2 = 31    → Item names/descriptions
RecType3         → Item Code (matches Help1.Code where MasterType=6)
```

### Status Codes
```
0 → Active/Current
1 → Deleted/Inactive (not present in current data)
```

### NameOrAlias Codes
```
1 → Primary Name
2 → Alias/Alternate Name
```

---

## Usage Notes

1. **Help1** is the **primary lookup table** for all master data:
   - Use `Code` field to lookup any master by its ID
   - Filter by `MasterType` to get specific entity types
   - Filter by `RecType` for specific views (name vs alias)
   - Filter by `Status = 0` for active records only

2. **Help2** is a **cross-reference table** for items:
   - Links Item Codes (RecType3) to various attributes
   - RecType2=31 contains item names
   - RecType2=7 contains item reference numbers/codes
   - Used for searching items by different criteria

3. **Key Relationships**:
   - `Help1.Code` = `MasterCode1` in many transaction tables
   - `Help1.ParentGroup` references another `Help1.Code` (hierarchy)
   - `Help2.RecType3` references `Help1.Code` where `MasterType=6`

4. **Important Patterns**:
   - Accounts (MasterType=2) have multiple RecType entries:
     - RecType=1: Account name
     - RecType=102: Mobile number
     - RecType=103: Phone number
     - RecType=104: Contact number
     - RecType=106: Address
   - Items (MasterType=6) have two entries:
     - NameOrAlias=1: Item name
     - NameOrAlias=2: Item code/alias
