# BillingDet Table Analysis

## Overview

The **BillingDet** table stores party billing details linked to vouchers in the Busy Accounting database. This is a critical table for invoice processing and payment reminders as it contains contact information (mobile numbers, emails) and addresses per transaction.

**Table Statistics:**
- **Total Rows:** 6,848
- **Total Columns:** 31
- **Relationship:** One-to-One with Tran1 (via VchCode)

---

## Table Structure

| Column Name | Data Type | Max Length | Purpose |
|-------------|-----------|------------|---------|
| **VchCode** | Integer | 10 | **Primary key linking to Tran1** |
| **PartyName** | String | 60 | Customer/Billing party name |
| **Address1** | String | 40 | Billing address line 1 |
| **Address2** | String | 40 | Billing address line 2 |
| **Address3** | String | 40 | Billing address line 3 (City/State/PIN) |
| **Address4** | String | 40 | Billing address line 4 |
| **STNo** | String | 30 | Sales Tax Number (legacy) |
| **CSTNo** | String | 30 | Central Sales Tax Number (legacy) |
| **ECCCode** | String | 20 | Excise Control Code (legacy) |
| **ExciseRegNo** | String | 30 | Excise Registration (legacy) |
| **PLANo** | String | 20 | PLA Number (legacy) |
| **Range** | String | 80 | Excise Range (legacy) |
| **Division** | String | 80 | Excise Division (legacy) |
| **Collectorate** | String | 40 | Excise Collectorate (legacy) |
| **MobileNo** | String | 255 | **Customer mobile number(s)** |
| **Email** | String | 255 | **Customer email address** |
| **DrugLicenceNo1** | String | 40 | Drug License Number 1 |
| **DrugLicenceNo2** | String | 40 | Drug License Number 2 |
| **ITPAN** | String | 20 | Income Tax PAN |
| **StateCode** | Integer | 10 | State code for GST |
| **GSTNo** | String | 30 | **GST Registration Number** |
| **TypeOfDealer** | Integer | 5 | Dealer type (0=Unreg, 1=Regular, 2=Composition) |
| **AdharNo** | String | 255 | Aadhaar Number |
| **PartyNameSL** | String | 255 | **Shipping Party Name** (SL = Shipping Location) |
| **Address1SL** | String | 255 | Shipping address line 1 |
| **Address2SL** | String | 255 | Shipping address line 2 |
| **Address3SL** | String | 255 | Shipping address line 3 |
| **Address4SL** | String | 255 | Shipping address line 4 |
| **FSSAINo** | String | 255 | FSSAI License Number |
| **UdyamNo** | String | 255 | Udyam Registration Number |
| **MSMEType** | Integer | 5 | MSME Classification |

---

## Voucher Linkage Analysis

### Relationship with Tran1

The BillingDet table is linked to the main transaction table (Tran1) through the **VchCode** column:

| Metric | Value |
|--------|-------|
| Unique VchCodes in BillingDet | 6,848 |
| VchCodes matching Tran1 | 6,848 |
| Orphaned records (no matching Tran1) | 0 |

**Key Finding:** Perfect 1:1 relationship with Tran1. Every billing detail record has a corresponding transaction.

### Voucher Types

All BillingDet records are linked to the following voucher types:

| VchType | Count | Description |
|---------|-------|-------------|
| 9 | 6,841 | Sales Invoice (Sales) |
| 26 | 6 | Sales Invoice (Sales Return) |
| 16 | 1 | Purchase Invoice |

**Key Finding:** 99.9% are sales invoices (VchType=9), making this table primarily for customer billing details on sales transactions.

---

## Contact Information Analysis

### Mobile Numbers

| Metric | Count | Percentage |
|--------|-------|------------|
| Total records | 6,848 | 100% |
| With mobile numbers | 4,244 | **62.0%** |
| Without mobile numbers | 2,604 | **38.0%** |

**Key Finding:** Only 62% of invoices have mobile numbers stored. This is a **critical gap** for WhatsApp payment reminders.

#### Mobile Number Format

Mobile numbers are stored as comma-separated strings with multiple formats:

```
9817998176,98960-54400          (Multiple numbers)
9575731286,8109412656           (Multiple numbers)
9214064643                      (Single number)
9412677053,9837351210           (Multiple numbers)
```

**Pattern:** Multiple mobile numbers per invoice are separated by commas. Numbers may include hyphens.

#### Sample Mobile Numbers

| VchCode | Party Name | Mobile Numbers |
|---------|------------|----------------|
| 22 | UPHAR EMPORIUM-KARNAL | 9817998176,98960-54400 |
| 1 | KRISHNA SUITING SHIRTING - BINA | 9575731286,8109412656 |
| 3 | SAJAWAT HANDLOOM-SONIPAT | 9991111133,9254146104 |
| 24 | J.B.N HANDLOOMS-AKOLA | 9421830515,8390081363 |
| 28 | PANIPAT HANDLOOM-KARNAL | 9215244900,8053433789,8708073909 |

### Email Addresses

| Metric | Count | Percentage |
|--------|-------|------------|
| Total records | 6,848 | 100% |
| With email | 592 | **8.6%** |
| Without email | 6,256 | **91.4%** |

**Key Finding:** Only 8.6% of invoices have email addresses. This is a **major gap** for email payment reminders.

#### Sample Email Addresses

| VchCode | Party Name | Email |
|---------|------------|-------|
| 22 | UPHAR EMPORIUM-KARNAL | upharemporium23@gmail.com |
| 3 | SAJAWAT HANDLOOM-SONIPAT | din_1573@ymail.com |
| 124 | ATUL INTERNATIONAL-PANIPAT | atulinternational11@gmail.com |
| 167 | SHRI SATYA TRADING CO - PANIPAT | sanjaygakhar777@gmail.com |
| 343 | RAJ HANDLOOM STORE - LUDHIANA | amitchugh@hotmail.com |

---

## Address Information

### Billing Address

| Address Field | Records with Data | Percentage |
|---------------|-------------------|------------|
| Address1 | 4,173 | 60.9% |
| Address2 | 4,037 | 59.0% |
| Address3 | 2,066 | 30.2% |
| Address4 | 191 | 2.8% |

**Key Finding:** 60.9% of invoices have complete billing addresses (Address1 + Address2).

#### Sample Billing Address

```
VchCode: 22
Party: UPHAR EMPORIUM-KARNAL
Address1: SHOP NO. C-672-673, 2ND FLOOR
Address2: NEAR UPHAR EMPORIUM, KARAN GATE, Karnal
Address3: Haryana, 132001
Address4: (empty)
```

### Shipping Address (SL Fields)

| Address Field | Records with Data | Percentage |
|---------------|-------------------|------------|
| PartyNameSL | 0 | 0.0% |
| Address1SL | 0 | 0.0% |
| Address2SL | 0 | 0.0% |
| Address3SL | 0 | 0.0% |
| Address4SL | 0 | 0.0% |

**Key Finding:** Shipping address fields (SL = Shipping Location) are **completely empty** in this database. All addresses stored are billing addresses.

---

## Tax Registration Analysis

### GST Registration

| Metric | Count | Percentage |
|--------|-------|------------|
| Total records | 6,848 | 100% |
| With GST Number | 3,577 | **52.2%** |
| Without GST Number | 3,271 | **47.8%** |
| With PAN | 3,481 | **50.8%** |

**Key Finding:** Only 52.2% of invoices have GST numbers. This suggests a mix of registered and unregistered dealers.

### Type of Dealer Distribution

| TypeOfDealer | Count | Percentage | Description |
|--------------|-------|------------|-------------|
| 0 | 3,262 | 47.6% | Unregistered |
| 1 | 3,251 | 47.5% | Regular Registered |
| 2 | 335 | 4.9% | Composition Dealer |

**Key Finding:** Nearly equal split between registered (52.4%) and unregistered (47.6%) dealers.

#### Sample GST Numbers

| VchCode | Party Name | GST Number | Type |
|---------|------------|------------|------|
| 22 | UPHAR EMPORIUM-KARNAL | 06BEKPC9578J1ZY | Regular (1) |
| 1 | KRISHNA SUITING SHIRTING - BINA | 23CVEPG3875N1Z8 | Regular (1) |
| 3 | SAJAWAT HANDLOOM-SONIPAT | 06AAIPC3973E1ZX | Composition (2) |
| 24 | J.B.N HANDLOOMS-AKOLA | 27ACIPN8717F1ZC | Regular (1) |

---

## Geographic Distribution

### Top 10 States by Invoice Count

| StateCode | Invoice Count | Percentage |
|-----------|---------------|------------|
| 1171 | 4,119 | 60.2% |
| 1187 | 512 | 7.5% |
| 1164 | 474 | 6.9% |
| 1192 | 389 | 5.7% |
| 1168 | 314 | 4.6% |
| 1188 | 222 | 3.2% |
| 1170 | 171 | 2.5% |
| 1172 | 119 | 1.7% |
| 1179 | 97 | 1.4% |
| 4145 | 91 | 1.3% |

**Key Finding:** 60.2% of all invoices are from StateCode 1171 (likely Haryana, based on GST numbers starting with '06').

---

## Complete Sample Record

Here's a complete example of a BillingDet record:

```json
{
  "VchCode": 22,
  "PartyName": "UPHAR EMPORIUM-KARNAL",
  "Address1": "SHOP NO. C-672-673, 2ND FLOOR",
  "Address2": "NEAR UPHAR EMPORIUM, KARAN GATE, Karnal",
  "Address3": "Haryana, 132001",
  "Address4": "",
  "STNo": "",
  "CSTNo": "",
  "ECCCode": "",
  "ExciseRegNo": "",
  "PLANo": "",
  "Range": "",
  "Division": "",
  "Collectorate": "",
  "MobileNo": "9817998176,98960-54400",
  "Email": "upharemporium23@gmail.com",
  "DrugLicenceNo1": "",
  "DrugLicenceNo2": "",
  "ITPAN": "AASPC2569A",
  "StateCode": 1171,
  "GSTNo": "06BEKPC9578J1ZY",
  "TypeOfDealer": 1,
  "AdharNo": "",
  "PartyNameSL": "",
  "Address1SL": "",
  "Address2SL": "",
  "Address3SL": "",
  "Address4SL": "",
  "FSSAINo": "",
  "UdyamNo": "",
  "MSMEType": 0
}
```

---

## Key Findings for Payment Reminders

### Strengths

1. **Perfect Data Integrity**: 100% of BillingDet records link correctly to Tran1
2. **Mobile Coverage**: 62% of invoices have mobile numbers (4,244/6,848)
3. **Complete Billing Info**: Party name, address, GST details available for 60%+ invoices
4. **Multiple Contact Support**: MobileNo field supports multiple comma-separated numbers

### Gaps & Limitations

1. **Missing Mobile Numbers**: 38% of invoices lack mobile numbers (2,604 records)
   - **Impact**: Cannot send WhatsApp payment reminders to these customers
   - **Recommendation**: Update Master1 with mobile numbers for these parties

2. **Low Email Coverage**: Only 8.6% have email addresses (592/6,848)
   - **Impact**: Email reminders not viable for most customers
   - **Recommendation**: Focus on WhatsApp/SMS over email

3. **No Shipping Addresses**: Shipping Location (SL) fields are completely empty
   - **Impact**: All addresses are billing addresses only
   - **Note**: This is typical for wholesale businesses

4. **Unregistered Dealers**: 47.6% are unregistered (TypeOfDealer=0)
   - **Impact**: These may be cash customers with limited contact info
   - **Recommendation**: Prioritize registered dealers for payment reminders

### Recommendations for Implementation

1. **Dual Source Strategy**: Use BillingDet.MobileNo as primary, fallback to Master1.Mobile
2. **Data Enrichment**: Prompt users to add mobile numbers in Busy for missing records
3. **Mobile Parsing**: Handle comma-separated mobile numbers (split and validate)
4. **State Filtering**: Focus on StateCode 1171 (60% of business) for initial rollout
5. **Registration Filter**: Prioritize TypeOfDealer=1 (Regular) for payment reminders

---

## SQL Queries for Reference

### Get Contact Info for Payment Reminders
```sql
SELECT 
    bd.VchCode,
    bd.PartyName,
    bd.MobileNo,
    bd.Email,
    bd.GSTNo,
    bd.TypeOfDealer,
    t1.VchDate,
    t1.VchNo
FROM BillingDet bd
INNER JOIN Tran1 t1 ON bd.VchCode = t1.VchCode
WHERE bd.MobileNo IS NOT NULL AND bd.MobileNo <> ''
ORDER BY t1.VchDate DESC
```

### Find Records Missing Mobile Numbers
```sql
SELECT 
    bd.VchCode,
    bd.PartyName,
    t1.VchDate,
    t1.VchNo,
    t1.VchAmt
FROM BillingDet bd
INNER JOIN Tran1 t1 ON bd.VchCode = t1.VchCode
WHERE bd.MobileNo IS NULL OR bd.MobileNo = ''
ORDER BY t1.VchAmt DESC
```

### Get Party-wise Mobile Numbers (for Master1 update)
```sql
SELECT 
    bd.PartyName,
    bd.MobileNo,
    COUNT(*) as invoice_count
FROM BillingDet bd
WHERE bd.MobileNo IS NOT NULL AND bd.MobileNo <> ''
GROUP BY bd.PartyName, bd.MobileNo
ORDER BY invoice_count DESC
```

---

## Conclusion

The BillingDet table is a **valuable source** of contact information for payment reminders, with 62% mobile coverage. However, the 38% gap in mobile numbers is significant and should be addressed by updating Master1 records. The table provides complete billing addresses and tax information, making it ideal for invoice-related communications.

**Priority for Payment Reminders:**
1. ✅ Use BillingDet.MobileNo (62% coverage)
2. ✅ Parse comma-separated mobile numbers
3. ⚠️ Address 38% gap in Master1
4. ❌ Email not viable (only 8.6% coverage)

---

*Analysis generated: 2026-02-23*
*Database: C:\Users\Vibhor\Desktop\COMP0012\db12025.bds*
