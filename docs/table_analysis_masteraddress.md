# MasterAddressInfo Table Analysis

## Overview

**Table:** MasterAddressInfo  
**Total Columns:** 75  
**Total Rows:** 10,336  
**Database:** db12025.bds  
**Analysis Date:** 2026-02-23

---

## 1. Relationship with Master1

### Key Finding: 1:1 Relationship

The MasterAddressInfo table has a **one-to-one (1:1) relationship** with Master1:

- **Total records:** 10,336
- **Records with MasterCode:** 10,336 (100%)
- **Unique MasterCode values:** 10,336

**Linkage:**
- **Foreign Key:** `MasterCode` in MasterAddressInfo
- **Primary Key:** `Code` in Master1
- **Relationship:** Each party in Master1 has exactly ONE corresponding address record

### Sample Linkage Data

| Master1.Name | Master1.Code | MAI.MasterCode |
|--------------|--------------|----------------|
| Cash | 1 | 1 |
| Profit & Loss | 2 | 2 |
| Stock | 3 | 3 |
| SALE | 4 | 4 |
| PURCHASE | 5 | 5 |

---

## 2. Address Structure

### Physical Address Fields (8 columns)

All 10,336 records have complete address data:

| Column | Type | Completeness |
|--------|------|--------------|
| Address1 | str | 100% (10,336/10,336) |
| Address2 | str | 100% (10,336/10,336) |
| Address3 | str | 100% (10,336/10,336) |
| Address4 | str | 100% (10,336/10,336) |
| Address1SL | str | 100% (10,336/10,336) |
| Address2SL | str | 100% (10,336/10,336) |
| Address3SL | str | 100% (10,336/10,336) |
| Address4SL | str | 100% (10,336/10,336) |

**Note:** `AddressXSL` columns are likely for second language (Hindi) addresses.

### Location Code Fields (6 columns)

| Column | Type | Purpose |
|--------|------|---------|
| CountryCodeLong | int | Country reference |
| StateCodeLong | int | State reference |
| CityCodeLong | int | City reference |
| RegionCodeLong | int | Region reference |
| AreaCodeLong | int | Area reference |
| PINCode | str | Postal/ZIP code |

---

## 3. Contact Details

### Phone/Mobile Numbers

| Column | Records | Unique Values | Coverage |
|--------|---------|---------------|----------|
| **Mobile** | 4,571 | 4,305 | 44.2% |
| **TelNo** | 965 | 942 | 9.3% |
| **WhatsAppNo** | 4,567 | - | 44.2% |
| **Contact** | 397 | 381 | 3.8% |
| **TelNoResi** | 0 | 0 | 0% |

**Sample Mobile Numbers:**
- `9215011111,9254100251` (multiple numbers)
- `9992929903`
- `9215984393`
- `098290-95737`
- `7014348639`

**Sample TelNo (Landline):**
- `0180-26-32499`
- `0180-2647499`
- `080534-00564`
- `077938-42691`
- `7568555904`

### Email Addresses

| Metric | Value |
|--------|-------|
| Records with Email | 273 |
| Unique Emails | 266 |
| Coverage | 2.6% |

**Sample Emails:**
- `omhandloom7@gmail.com`
- `mailtoliberty@yahoo.co.in`
- `gruhsajjapune@yahoo.com`
- Some records contain non-email data (e.g., bank account numbers)

---

## 4. GST Registration

### GST Information

| Metric | Value |
|--------|-------|
| Records with GSTNo | 2,721 |
| Coverage | 26.3% |

**Sample GST Numbers:**

| Party Name | GST No |
|------------|--------|
| VARDHMAN HANDLOOM INDUSTRIES-PANIPAT | 06AAUPJ2384E1ZJ |
| PREM CHAND FABS - PANIPAT | 06AAJFP7017P1ZQ |
| GABA TEXTILES-PANIPAT | 06AINPG5883C1Z6 |
| VISHAL TEX PRINTS-JAIPUR | 08ADQPJ5638J2ZY |
| PAWAN ENTERPRISES - JAIPUR | 08BJCPS3928K1ZR |

**GST Number Pattern:**
- 15-character alphanumeric format
- State code (first 2 digits) matches StateCodeLong
- Format: `XXAAAAA0000X1X1`

---

## 5. Multiple Addresses Per Party

### Distribution

| # of Addresses | # of Parties | Percentage |
|----------------|--------------|------------|
| 1 | 10,336 | 100.0% |

**Finding:** There are NO parties with multiple addresses. Each party has exactly one address record.

This means:
- No separate shipping/billing addresses stored
- No multiple GST registrations per party
- Single contact information per party

---

## 6. Additional Registration Fields

### Tax & License Information

| Column | Type | Description |
|--------|------|-------------|
| GSTNo | str | GST Registration Number |
| TINNo | str | Tax Identification Number |
| LST | str | Local Sales Tax |
| CST | str | Central Sales Tax |
| ST37 | str | Sales Tax Form 37 |
| ITPAN | str | Income Tax PAN |
| ITWard | str | Income Tax Ward |
| LBTNo | str | Local Body Tax Number |
| DLNo | str | Drug License Number |
| DLNo2 | str | Drug License Number 2 |

### Excise Information

| Column | Description |
|--------|-------------|
| ExciseRegNo | Excise Registration Number |
| ECCCode | Excise Control Code |
| PLANo | PLA Number |
| Division | Excise Division |
| Range | Excise Range |
| Collectorate | Excise Collectorate |

### Service Tax

| Column | Description |
|--------|-------------|
| ServiceTaxNo | Service Tax Registration |
| SupplierType | Type of supplier |

---

## 7. Complete Column List

### Core Information (1-9)
1. **MasterCode** (int) - Link to Master1
2. **Address1** (str) - Address line 1
3. **Address2** (str) - Address line 2
4. **Address3** (str) - Address line 3
5. **Address4** (str) - Address line 4
6. **TelNo** (str) - Telephone number
7. **Fax** (str) - Fax number
8. **Email** (str) - Email address
9. **Mobile** (str) - Mobile number

### Tax Registration (10-16)
10. **LST** (str) - Local Sales Tax
11. **CST** (str) - Central Sales Tax
12. **ST37** (str) - Sales Tax Form 37
13. **TINNo** (str) - TIN Number
14. **LBTNo** (str) - Local Body Tax
15. **ITPAN** (str) - PAN Number
16. **ITWard** (str) - IT Ward

### Excise & Contact (17-23)
17. **Contact** (str) - Contact person name
18. **ExciseRegNo** (str) - Excise registration
19. **ECCCode** (str) - ECC Code
20. **PLANo** (str) - PLA Number
21. **Division** (str) - Excise division
22. **Range** (str) - Excise range
23. **Collectorate** (str) - Collectorate

### Custom Fields (24-33)
24-33. **OF1-OF10** (str) - Custom fields

### Tax & Classification (34-36)
34. **SupplierType** (str) - Supplier type
35. **ServiceTaxNo** (str) - Service tax number
36. **TelNoResi** (str) - Residential phone

### GST & Location Codes (37-43)
37. **GSTNo** (str) - GST Number
38. **CountryCodeLong** (int) - Country code
39. **StateCodeLong** (int) - State code
40. **CityCodeLong** (int) - City code
41. **RegionCodeLong** (int) - Region code
42. **AreaCodeLong** (int) - Area code
43. **ContDeptCodeLong** (int) - Contact department

### Logistics (44-49)
44. **PINCode** (str) - Postal code
45. **DLNo** (str) - Drug license 1
46. **DLNo2** (str) - Drug license 2
47. **Transport** (str) - Transport details
48. **Station** (str) - Railway station
49. **AccNo** (str) - Account number

### Dates (50-57)
50-57. **Date1-Date8** (datetime) - Date fields

### Custom Text Fields (58-67)
58-67. **C1-C10** (str) - Custom text fields

### Additional (68-70)
68. **M1** (str) - Custom field
69. **Distance** (float) - Distance
70. **TransportMode** (int) - Transport mode

### Second Language Address (71-74)
71. **Address1SL** (str) - Address 1 (Second Language)
72. **Address2SL** (str) - Address 2 (Second Language)
73. **Address3SL** (str) - Address 3 (Second Language)
74. **Address4SL** (str) - Address 4 (Second Language)

### Communication (75)
75. **WhatsAppNo** (str) - WhatsApp number

---

## 8. Key Findings for WhatsApp Gateway

### Contact Information Availability

For reminder notifications, the following data is available:

| Contact Type | Availability | Notes |
|--------------|--------------|-------|
| **Mobile** | 44.2% | Primary for SMS/WhatsApp |
| **WhatsAppNo** | 44.2% | Dedicated WhatsApp field |
| **TelNo** | 9.3% | Landline (less useful) |
| **Email** | 2.6% | Low coverage |

### Recommendations

1. **Use Mobile field** as the primary contact method (44% coverage)
2. **Check WhatsAppNo field** as alternative (44% coverage)
3. **Mobile and WhatsAppNo fields appear to overlap** - may contain same numbers
4. **Email is not reliable** (only 2.6% coverage)

### Data Quality Issues

1. **Mixed data in fields:**
   - Contact field contains both names and account numbers
   - Email field contains non-email data (bank accounts)
   - Mobile field may contain multiple numbers (comma-separated)

2. **Format variations:**
   - Phone numbers: with/without dashes, spaces
   - Mobile numbers: with/without leading zero
   - Some with area codes, some without

3. **Empty addresses:**
   - Some records (like Cash, Stock) have empty Address1-4
   - These are likely system/internal accounts

---

## 9. SQL Queries for Reference

### Get Party Contact Information

```sql
SELECT 
    m1.Code,
    m1.Name,
    mai.Mobile,
    mai.WhatsAppNo,
    mai.TelNo,
    mai.Email
FROM Master1 m1
JOIN MasterAddressInfo mai ON m1.Code = mai.MasterCode
WHERE m1.Code = ?
```

### Search by Phone Number

```sql
SELECT 
    m1.Code,
    m1.Name,
    mai.Mobile,
    mai.WhatsAppNo
FROM Master1 m1
JOIN MasterAddressInfo mai ON m1.Code = mai.MasterCode
WHERE mai.Mobile LIKE '%' + ? + '%'
   OR mai.WhatsAppNo LIKE '%' + ? + '%'
```

### Get GST Registration Details

```sql
SELECT 
    m1.Name,
    mai.GSTNo,
    mai.Address1,
    mai.Address2,
    mai.Address3,
    mai.Address4,
    mai.PINCode
FROM Master1 m1
JOIN MasterAddressInfo mai ON m1.Code = mai.MasterCode
WHERE mai.GSTNo IS NOT NULL
```

---

## 10. Summary Statistics

| Metric | Value |
|--------|-------|
| Total Records | 10,336 |
| Records with MasterCode | 10,336 |
| Unique Parties | 10,336 |
| Records with TelNo | 965 (9.3%) |
| Records with Mobile | 4,571 (44.2%) |
| Records with Email | 273 (2.6%) |
| Records with WhatsAppNo | 4,567 (44.2%) |
| Records with GSTNo | 2,721 (26.3%) |

---

## Conclusion

MasterAddressInfo is a **1:1 extension table** of Master1 containing:
- Complete address information (4 lines + 4 lines in second language)
- Contact details (Mobile/WhatsApp most populated at ~44%)
- Tax registration details (GST, TIN, Excise, etc.)
- Location codes for geographic references

**For WhatsApp reminders:** Focus on the **Mobile** and **WhatsAppNo** fields which have ~44% coverage across all parties.

---

*Analysis generated by: analyze_masteraddress.py*  
*Database: C:\Users\Vibhor\Desktop\COMP0012\db12025.bds*
