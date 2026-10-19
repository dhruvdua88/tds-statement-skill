# Form 144 (payments to non-residents) record layout

Generated from the department's own file-format workbook, `Form144_27Q_Q1-Q4_v1.2_22072026.xlsx`, sheet `FIleformat_R`. Every width, field number, name and remark below is read out of that workbook, and `tests/test_layout144.py` reads it back again on any machine that has the workbook. Do not hand-edit a number here; change the module and the test together.

Form 144 is the quarterly statement of tax deducted on payments other than salary made to non-residents. It replaced Form 27Q, and it has the record shape of Form 140 down to the field numbering, so the code that writes a statement is shared and only the content differs. Where this page says a field is mandatory, that is the workbook's M/O column talking; the remarks add conditions of their own, and those are quoted in full.

| Record | Fields | Workbook rows | Meaning |
|---|---:|---|---|
| FH | 18 | 22-39 | File header, once per file |
| BH | 72 | 44-115 | Batch header, once per batch |
| CD | 30 | 120-149 | Challan detail, once per challan |
| DD | 45 | 154-198 | Deductee detail, once per deductee |

A regular statement carries one batch, so a file is an FH, a BH, then for each challan a CD followed by its DD rows, in that order. Within a record the field number runs 1..n, so field n of a record that starts at row r sits in workbook row r - 1 + n. "Form col." is the printed column on the paper form where the workbook names one. "Module key" is the key in `scripts/layout144.py` that holds the field number, and a hyphen means this toolkit writes nothing into that field.

## FH record

| # | Field | Form col. | Type | Size | M/O | Module key | Remark |
|---:|---|---|---|---:|---|---|---|
| 1 | Line Number | NA | INTEGER | 9 | M | `line_no` | Running Sequence Number for each line in the file. |
| 2 | Record Type | NA | CHAR | 2 | M | `record_type` | Value should be "FH" signifying 'File Header' record |
| 3 | File Type | NA | CHAR | 4 | M | `file_type` | Value should be "NS1" for FN 144. |
| 4 | Upload Type | NA | CHAR | 2 | M | `upload_type` | Value should be R |
| 5 | File Creation Date | NA | DATE | 8 | M | `file_creation_date` | Mention the date of creation of the file in ddmmyyyy format. |
| 6 | File Sequence No. | NA | INTEGER | 9 | M | `file_sequence_no` | Indicates the running sequence number for the file. (Should be unique across all the files) |
| 7 | Uploader Type | NA | CHAR | 1 | M | `uploader_type` | Value should be D |
| 8 | TAN of Deductor | NA | CHAR | 10 | M | `tan` | TAN of Deductor |
| 9 | Total No. of Batches | NA | INTEGER | 9 | M | `total_batches` | Indicates the number of batches that the file contains. |
| 10 | Name of Return Preparation Utility | NA | CHAR | 75 | M | `utility_name` | Name of the software used for preparing the Quarterly e-TDS/TCS statement should be mentioned. |
| 11 | Record Hash (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 12 | FVU Version (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 13 | File Hash (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 14 | Sam Version (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 15 | SAM Hash (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 16 | SCM Version (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 17 | SCM Hash (Not applicable) | NA | NA | 0 | NA | - | No value should be specified |
| 18 | Consolidated file hash | NA | NA | 0 | NA | - | No value should be specified |

## BH record

| # | Field | Form col. | Type | Size | M/O | Module key | Remark |
|---:|---|---|---|---:|---|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | `line_no` | Running Sequence Number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | `record_type` | Value should be "BH" (Batch Header) for the batch header record |
| 3 | Batch Number | – | INTEGER | 9 | M | `batch_number` | Value must start with 1. |
| 4 | Count of Challan/transfer voucher Records | – | INTEGER | 9 | M | `num_challans` | Count of total number of challans/transfer vouchers contained within the batch. |
| 5 | Form Number | – | CHAR | 4 | M | `form_number` | Value must be 144 |
| 6 | Transaction Type (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 7 | Batch Updation Indicator (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 8 | Original Token Number (Token Number of Regular statement) - (Not applicable) of the statement | – | NA | 0 | O | - | No value should be specified |
| 9 | Token no. of previous regular statement (Form no. 144). | – | INTEGER | 15 | O | `token_previous` | If value present in field no. 52 is "Y", mandatory to mention 15 digit Token number of immediate previous regular statement for Form 144, else no value to be provided. |
| 10 | Token Number of the statement submitted -- (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 11 | Token Number date - (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 12 | Last TAN of Deductor / Collector ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 13 | TAN of Deductor | – | CHAR | 10 | M | `tan` | Mention the 10 Character TAN of the deductor. Should be all CAPITALS. |
| 14 | Receipt number (eight digit) provided by TIN | – | CHAR | 8 | NA | - | No value should be specified |
| 15 | PAN of Deductor | – | CHAR | 10 | M | `pan_deductor` | Mandatory to mention the PAN of the Deductor. If deductor is not required to have a PAN mention PANNOTREQD |
| 16 | Assessment Yr | – | INTEGER | 6 | M | `assessment_year` | Assessment year e.g. value should be 200809 for Assessment Year 2008-09. Value should be greater than or equal to 200809. |
| 17 | Tax Year | – | INTEGER | 6 | M | `tax_year` | Tax Year (YYYYYY) as per Act; e.g., 202627 for Tax Year 2026-27 |
| 18 | Period | – | CHAR | 2 | M | `period` | Valid values Q1, Q2, Q3, Q4 of the financial Year. Q1 for 1st Quarter, Q2 for 2nd Quarter, Q3 for 3rd Quarter and Q4 for 4th Quarter. |
| 19 | Name of Deductor | – | CHAR | 75 | M | `name_deductor` | Mention the Name of the Employer / Deductor I.e. Employer / Deductor who deducts tax. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 20 | Deductor Address 6 (Country/Region) | NA | CHAR | 25 | M | `addr_country` | Mention the address line 6 of the Employer. Only special characters are not allowed under this field. |
| 21 | Deductor Address1 (Flat/Door/Block number) | – | CHAR | 25 | M | `addr1` | Mention the address line 1 of the Employer. Only special characters are not allowed under this field. |
| 22 | Deductor Address2 (Post Office) | – | CHAR | 25 | O | `addr2` | Mention the address line 2 of the Employer. Only special characters are not allowed under this field. |
| 23 | Deductor Address3 (Road/Street/Block/Sector) | – | CHAR | 25 | O | `addr3` | Mention the address line 3 of the Employer. Only special characters are not allowed under this field. |
| 24 | Deductor Address4 (Area/locality) | – | CHAR | 25 | O | `addr4` | Mention the address line 4 of the Employer. Only special characters are not allowed under this field. |
| 25 | Deductor Address5 (District) | – | CHAR | 25 | O | `addr5` | Mention the address line 5 of the Employer. Only special characters are not allowed under this field. |
| 26 | Deductor's Address - State | – | INTEGER | 2 | M | `state_code` | Numeric code for state. For list of State codes, refer to the Annexure 1 below. |
| 27 | Deductor's Address - Pincode | – | INTEGER | 6 | M | `pin` | PIN Code of Deductor . |
| 28 | Deductor's Email ID | – | CHAR | 75 | M | `deductor_email` | Valid E-mail should be provided. 1. Email format must be checked -atleast @ and '.' should be mentioned. 2. Both @ and '.' should be preceded and succeeded by atleast one character. 3. At least one '.' should come after '@'. 4. All printable characters allowed except '^' and space. 5. This field is mandatory if no value is provided under field no. 42 i.e. "Responsible Person's Email ID -1" of Batch Header. E-mail id of deductor/collector or person responsible for deducting/collecting tax should be provided. |
| 29 | Deductor Contact Country Code | – | INTEGER | 5 | M | `deductor_country_code` | Country calling code for deductor contact number (e.g., 91 for India). |
| 30 | Deductor Contact Number | – | CHAR | 10 | M | `deductor_phone` | Deductor contact number without country code; digits only. Max 15. |
| 31 | Filler 1 | NA | NA | 0 | O | - | No value should be specified |
| 32 | Deductor Type | – | CHAR | 1 | M | `deductor_category` | Deductor category code to be mentioned as per Annexure 4 |
| 33 | Name of Person responsible for Deduction | – | CHAR | 75 | M | `rp_name` | Mention the Name of Person responsible for paying salary on behalf of the deductor. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 34 | Designation of the Person responsible for Deduction | – | CHAR | 20 | M | `rp_designation` | Mention the designation of Person responsible for paying salary on behalf of the deductor. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 35 | Responsible Person's Address1 (Flat/Door/Block number) | – | CHAR | 25 | M | `rp_addr1` | Mention the address line 1 of the responsible Person. Only special characters are not allowed under this field. |
| 36 | Responsible Person's Address2 (Post Office) | – | CHAR | 25 | O | `rp_addr2` | Mention the address line 2 of the responsible Person. Only special characters are not allowed under this field. |
| 37 | Responsible Person's Address3 (Road/Street/Block/Sector) | – | CHAR | 25 | O | `rp_addr3` | Mention the address line 3 of the responsible Person. Only special characters are not allowed under this field. |
| 38 | Responsible Person's Address4 (Area/locality) | – | CHAR | 25 | O | `rp_addr4` | Mention the address line 4 of the responsible Person. Only special characters are not allowed under this field. |
| 39 | Responsible Person's Address5(District) | – | CHAR | 25 | O | `rp_addr5` | Mention the address line 5 of the responsible Person. Only special characters are not allowed under this field. |
| 40 | Responsible Person's State | – | INTEGER | 2 | M | `rp_state_code` | Numeric code for state. For list of State codes, refer to the Annexure 1 below. |
| 41 | Responsible Person's PIN | – | INTEGER | 6 | M | `rp_pin` | PIN Code of Responsible Person . |
| 42 | Responsible Person's Email ID -1 | – | CHAR | 75 | M | `rp_email` | Valid E-mail should be provided. 1. Email format must be checked -atleast @ and '.' should be mentioned. 2. Both @ and '.' should be preceded and succeeded by atleast one character. 3. At least one '.' should come after '@'. 4. All printable characters allowed except '^' and space. 5. This field is mandatory if no value is provided under field no. 28 i.e. "Deductor's Email ID" of Batch Header. E-mail id of deductor/collector or person responsible for deducting/collecting tax should be provided. |
| 43 | Responsible Persons country region | NA | CHAR | 25 | M | `rp_country` | Mention the country of the responsible person . Only special characters are not allowed under this field. |
| 44 | Responsible Person Contact Country Code | – | INTEGER | 5 | M | `rp_country_code` | Country calling code for person responsible contact number (e.g., 91). |
| 45 | Responsible Person Contact Number | – | CHAR | 10 | M | `rp_phone` | Contact number (digits) for person responsible; max 15. |
| 46 | Filler 3 | NA | NA | 0 | O | - | No value should be specified |
| 47 | Batch Total of - Total of Deposit Amount as per Challan | – | INTEGER | 15 | M | `batch_total` | Mention the Total of Deposit Amount as per Challan.The value here should be same as sum of values in field 'Total of Deposit Amount as per Challan' in the 'Challan Detail' record ( please refer to the Challan Detail' record section below ). Paisa Field (Decimal Value) of the Amount must be 00. |
| 48 | Unmatched challan count | – | CHAR | 9 | O | - | No value to be specified. |
| 49 | Count of Salary Details Records (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 50 | Batch Total of - Gross Total Income as per Salary Detail (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 51 | Filler 4 | NA | NA | 0 | O | - | No value should be specified |
| 52 | Whether regular statement for Form 144 filed for earlier period | – | CHAR | 1 | M | `regular_earlier` | "Y" if regular statement for Form 144 has been filed for earlier period, else value "N" should be provided. |
| 53 | Last Deductor Type | – | CHAR | 1 | NA | - | No value should be specified |
| 54 | State Name | – | CHAR | 2 | O | `state_name` | Numeric code for state should be mentioned as per Annexure 5. Mandatory if deductor type is State Govt. (code S), Statutory body - State Govt. (code E), Autonomous body - State Govt. code H) and Local Authority - State Govt. (code N). For other deductor category no value should be provided. |
| 55 | Filler 5 | NA | NA | 0 | O | - | No value should be specified |
| 56 | Filler 6 | NA | NA | 0 | O | - | No value should be specified |
| 57 | Ministry Name | NA | CHAR | 3 | O | `ministry_code` | Numeric code for Ministry name should be provided. For list of Ministry name codes, refer to the Annexure 3 below. Mandatory for following deductor types: Central Govt (A), Statutory body - Central Govt. (D) & Autonomous body - Central Govt. (G). Optional for deductor type Statutory body - State Govt. (E), Autonomous body - State Govt. (H), Local Authority - Central Govt. (L) & Local Authority -State Govt. (N). For other deductor type no value should be provided. |
| 58 | Ministry Name (Others) | NA | CHAR | 150 | O | `ministry_name` | If numeric code '99' (i.e. Other) is provided in Ministry Name field then value in Ministry Name "Other" field should be provided |
| 59 | PAN of Responsible Person | – | CHAR | 10 | M | `rp_pan` | Quote ten digit valid PAN of the person responsible (as quoted in field no. 33 above) for deducting tax. |
| 60 | Filler 7 | NA | NA | 0 | O | - | No value should be specified |
| 61 | Filler 8 | NA | NA | 0 | O | - | No value should be specified |
| 62 | Filler 9 | NA | NA | 0 | O | - | No value should be specified |
| 63 | Filler 10 | NA | NA | 0 | O | - | No value should be specified |
| 64 | Filler 11 | NA | NA | 0 | O | - | No value should be specified |
| 65 | Filler 12 | NA | NA | 0 | O | - | No value should be specified |
| 66 | Filler 13 | NA | NA | 0 | O | - | No value should be specified |
| 67 | Filler 14 | NA | NA | 0 | O | - | No value should be specified |
| 68 | Account Office Identification Number (AIN) of PAO/ TO/ CDDO | – | CHAR | 7 | O | `ain` | Mandatory to mention value for statements pertaining to FY 2013-14 onwards. Applicable only in case the deductor category is "Central Govt." or "State Govt." and mode of deposit of TDS/TCS is through 'Book Entry' i.e., value in the field no. 37 of challan/ transfer voucher details is "Y". Mention AIN of the below: 1) Pay and Account Office (PAO) 2) Treasure Office (TO) 3) Cheque Drawing and Disbursing Officer (CDDO) |
| 69 | Goods and Service Tax Number (GSTN) | – | CHAR | 15 | O | `gstin` | Mention 15 digit valid Goods and Service Tax Number (GSTIN). |
| 70 | Count of Section 194P Detail Records (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 71 | Batch Total of - Gross Total Income as per Section 194P Detail (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 72 | Record Hash (Not applicable) | – | NA | 0 | O | - | No value should be specified |

## CD record

| # | Field | Form col. | Type | Size | M/O | Module key | Remark |
|---:|---|---|---|---:|---|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | `line_no` | Running sequence number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | `record_type` | Value "CD" (Challan Detail) for Challan Detail record |
| 3 | Batch Number | – | INTEGER | 9 | M | `batch_number` | Value should be same as 'Batch Number' field in 'Batch Header' record. |
| 4 | Challan-Detail Record Number | A | INTEGER | 9 | M | `challan_no` | Running serial number for 'Challan Detail' records in a batch. Should start with 1 |
| 5 | Count of Deductee / Party Records | – | INTEGER | 9 | M | `num_deductees` | Count of total number of 'Deductee Detail Records' within e-TDS statement. Value Should be >= 0 |
| 6 | NIL Challan Indicator | – | CHAR | 1 | M | `nil_challan` | Value should be "N". In cases where no tax has been deposited in bank, value should be "Y" (applicable in case of NIL return) |
| 7 | Challan Updation Indicator (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 8 | Total tax Deducted | B | INTEGER | 15 | M | `tax` | Mention the amount of "Income Tax" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , i.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 9 | Total Interest | C | INTEGER | 15 | M | `interest` | Mention the amount of "Interest" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 10 | Total fee | D | INTEGER | 15 | M | `fee` | Mention the amount of "Fee" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 11 | Total Penalty/ Others | E | INTEGER | 15 | M | `penalty` | Mention the amount of "Penalty" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 12 | Total of Deposit Amount as per Challan/Total Amount adjusted through Book Adjustment (Total of values in B+C+D+E) | F | INTEGER | 15 | M | `total` | Mention the amount of 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. Value in this field should be equal to total of values in column numbers B, C, D, E. In case of challan (i.e. value under field 13 is C), value in this field should be greater than or equal to: Total tax deposited amount (field no. 25 of all deductee details mapped to corresponding challan) + Interest allocation (field no. 24 of challan details) + Other allocation (field no. 25 of challan details) + Fee amount (field no. 10 of challan details) In case of transfer voucher (i.e. value under field 13 is B), value in this field should be greater than or equal to: Total tax deposited amount (field no. 25 of all deductee details mapped to corresponding challan) + Interest allocation (field no. 24 of challan details) + Other allocation (field no. 25 of challan details) |
| 13 | Mode of payment of tax (by way of challan/by way of book adjustment) | G | CHAR | 1 | O | `challan_mode` | Allowed values C or B If Transfer Voucher Number is provided this is mandatory and only allowed value is 'B'. If Bank Challan Number is provided , then mention value as "C". For a Nil statement no value to be provided. Value 'C' to be provided, if values under field no. 15 of DD details are '1059' & '1061'. |
| 14 | Last BSR Code/ Form 24G Receipt Number ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 15 | BSR Code/ Form 24G Receipt Number | H | INTEGER | 7 | M | `bsr_code` | In case TDS deposited by 1) Challan:BSR Code of the receiving branch 2) Book Adjustment: Quote seven digit receipt number provided by AO. Applicable for govt. deductor/ collector where TDS is deposited by book entry. 3) No value to be quoted in case of Nil Statement (value in field "NIL Challan Indicator" field is "Y"). |
| 16 | Last Bank Challan No/DDO Serial Number ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 17 | Bank Challan No/DDO Serial Number | J | INTEGER | 5 | O | `challan_serial` | Challan Number issued by Bank if value in field G is C DDO Serial Number if value in column G is B Applicable to both Govt and Non Govt, Non-Nil statements. No value is required to be provided in case of a NIL return (i.e. the cases in which the value in field 'NIL Challan Indicator' is "Y"). |
| 18 | Last Date of 'Bank Challan No / DDO Serial Number' ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 19 | Date of 'Bank Challan / DDO Serial Number' (DDMMYYYY) | I | DATE | 8 | M | `challan_date` | Date of payment of tax to Govt. It can be any date on or after 1st April of immediate previous financial year for which the return is prepared. Value should be equal to last date of respective quarter if the value in field "NIL Challan Indicator" is "Y". Date of 'Bank Challan / Book Adjustment' should be within the respective quarter for which statement is being filed, in case of minor head code value selected under field no. 23 is '100'. Also this date has to be on or before date present under field 'Date on which Amount paid / Credited' field no. 19 of DD record (which is mapped to this challan with minor head code value '100') |
| 20 | Last Total of Deposit Amount as per Challan ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 21 | Total Tax Deposited Amount as per Deductee annexure (Total Sum of column no. U) for the specified challan | – | DECIMAL | 15 | M | `total_deductee_tax` | Mention the sum of 'Deductee Deposit Amount' of the underlying Deductee Records |
| 22 | Total Tax Deducted Amount as per Deductee annexure (Total sum of Column no. S) for the specified challan | – | DECIMAL | 15 | M | `deductee_tax` | Total sum of tax deducted amount of the deductee details for the respective Challan |
| 23 | Minor Head of Challan | K | INTEGER | 3 | O | `minor_head` | Mention value as marked on challan - refer Annexure 7 for minor head For Minor head code 100: If DD details are having section code '1059', or '1061', then minimum 1 deductee should be there for challans having minor head code 100. |
| 24 | Interest Allocation | – | INTEGER | 15 | M | `interest_allocation` | Mention interest allocation. Only integer values are allowed. The value of 1000 should be represented as 1000.00 in this field. Mention value as provided in field no. 9 of CD details. |
| 25 | Others Allocation | – | INTEGER | 15 | M | `other_allocation` | Mention fees allocation. Only integer values are allowed for this field. The value of 1000 should be represented as 1000.00 in this field. Mention value as provided in field no. 11 of CD details. |
| 26 | Filler 3 | – | NA | 0 | O | - | No value should be specified |
| 27 | Filler 4 | – | NA | 0 | O | - | No value should be specified |
| 28 | Filler 5 | – | NA | 0 | O | - | No value should be specified |
| 29 | Filler 6 | – | NA | 0 | O | - | No value should be specified |
| 30 | Record Hash (Not applicable) | – | NA | 0 | O | - | No value should be specified |

## DD record

| # | Field | Form col. | Type | Size | M/O | Module key | Remark |
|---:|---|---|---|---:|---|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | `line_no` | Running Sequence Number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | `record_type` | Value "DD"(Deductee Detail) for Deductee-detail record |
| 3 | Batch Number | – | INTEGER | 9 | M | `batch_number` | Value should be same as 'Batch Number' field in 'Batch Header' record |
| 4 | Deductee / Party Detail Record No | A | INTEGER | 9 | M | `deductee_serial` | Running serial number for 'Deductee Detail' records in a batch. |
| 5 | Challan reference Number | B | INTEGER | 9 | M | `challan_no` | Running serial number for 'Challan Detail' records in a batch. |
| 6 | Mode | – | CHAR | 1 | M | `record_status` | Value should be O |
| 7 | Last deductee PAN ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 8 | Deductee's PAN | C | CHAR | 10 | M | `pan` | PAN of the deductee. If available should be Valid PAN Format. There may be deductees who have not been issued PAN however who have applied for a PAN and have given adequate declaration to the deductor indicating the same. In such cases, deduction schedule in the statement will not reflect PAN and instead state PAN Ref. Number for the deductee. The deductor will however have to mention ‘PANAPPLIED’ in place of PAN. If the deductee is not sure of the PAN format he will have to mention 'PANINVALID'. However if the deductee has not given any declaration, deductor will have to mention ‘PANNOTAVBL’ in place of PAN. For section codes '1059' or '1061', no default PAN values should be allowed under this field. That means default PAN values in case of non-availablity of valid PAN ('PANNOTAVBL', 'PANAPPLIED', 'PANINVALID') will not be allowed for these sections. |
| 9 | Name of the Deductee | D | CHAR | 75 | M | `name` | Mention the Name of the deductee. |
| 10 | Remarks 1 (for future use) | – | NA | 0 | O | - | No value should be specified |
| 11 | Remarks 2 (for future use) | – | NA | 0 | O | - | No value should be specified |
| 12 | Status | I | INTEGER | 2 | M | `status` | As per Annexure 8 |
| 13 | Remarks 4 (for future use) | – | NA | 0 | O | - | No value should be specified |
| 14 | Whether deductee opting out of taxation regime u/s 202(1) | M | CHAR | 1 | M | `opting_out` | Value should be Y/N (Yes or No) |
| 15 | Section Code | J | CHAR | 4 | M | `section` | As per Annexure 2 |
| 16 | Nature of Remittance | K | INTEGER | 2 | O | `nature_of_remittance` | Mandatory to mention values for sections present under Annexure 9. For all other sections, no value should be specified. |
| 17 | Country to which remittance is made | L | INTEGER | 3 | M | `country_code` | Mention country numeric code as per Annexure 10 |
| 18 | Whether the total amount of tax deducted as mentioned in Column (S) has been deposited (Yes/No) | T | CHAR | 1 | M | `deposited` | Value should either "Y" or "N" |
| 19 | Date of payment / Credited (dd/mm/yyyy) | N | DATE | 8 | M | `payment_date` | Date on which Amount paid/ Credited /Debited to deductee. The value under the “Date of Payment / Date on which Amount Collected / Debited” field shall fall within the quarter and financial year to which the statement pertains· |
| 20 | Amount Paid/ Credited | O | DECIMAL | 15 | M | `amount_paid` | Mention the Amount paid to deductee. Value should always be greater than 0.00 |
| 21 | Whether the amount paid or credited is grossed up as per section 393(10) | P | CHAR | 1 | M | `grossed_up` | Value should be Y/N (Yes or No) |
| 22 | Amount of cash withdrawal in excess of Rs. 1 crore as referred to in section 393(3) [Table: Sl. No. 5] (in case of person other than co- operative society) | Q | DECIMAL | 15 | O | `cash_1cr` | Mandatory to mention value under this field only when value under field Section Code (field no. 15) of DD records is "section 393(3), i.e. section code 1065", else no value should be specified. |
| 23 | Amount of cash withdrawal which is in excess of Rs. 3 Crore for cases covered by section 393(3) [Table: Sl. No. 5] (in case of co- operative societies) | R | DECIMAL | 15 | O | `cash_3cr` | Mandatory to mention value under this field only when value under field Section Code (field no. 15) of DD records is "section 393(3), i.e. section code 1064", else no value should be specified. |
| 24 | Total Tax Deducted | S | DECIMAL | 15 | M | `tds` | Decimal with precision value 2 is allowed. In case value present under field 15 is 1059' or '1061', then value under this field should be 0.00. |
| 25 | Total Tax Deposited | U | DECIMAL | 15 | M | `total_tds` | Decimal with precision value 2 is allowed. In case value present under field 15 is 1059' or '1061', then value under this field should be 0.00. |
| 26 | Last total Tax deducted (Used for Verification) (Not Applicable) | – | NA | 0 | O | - | No value should be specified |
| 27 | Date of deduction (dd/mm/yyyy) | V | DATE | 8 | M | `deduction_date` | Date of tax deduction. Mandatory if 'Total tax deducted' is greater than Zero (0.00) . No value needs to be specified if 'Total Tax Deducted' is Zero (0.00) . Date to be mentioned in DDMMYYYY format. Also, this date should not be less than the relevant quarter. E.g. If the statement is being prepared for Q2 of Tax Year 2026-27, then date of deduction should be greater than or equal to 01/07/2026. |
| 28 | Rate at which Tax Deducted | W | DECIMAL | 7 | M | `rate` | Rate at which Tax is deducted, with decimal precision of 4 point. E.g. if the rate is 2 then the same should be mentioned as 2.0000. If value in field 'Total tax collected' is 0.00 then rate at which tax deducted should be 0.0000 In case value present under field 15 is 1059', or '1061', then value under this field should be 0.00. |
| 29 | Remarks 9 (for future use) | – | NA | 0 | O | - | No value should be specified |
| 30 | Whether rate of TDS is as per IT Act (a) or DTAA (b) | Z | CHAR | 1 | M | `rate_basis` | Allowed values 'A' or 'B' |
| 31 | Unique acknowledgement number of the corresponding Form No. 15CA [FN 144], if applicable | AA | CHAR | 26 | O | `form15ca` | Mention value of Unique Identification Number of Form No. 121 |
| 32 | Reason for non-deduction /lower deduction/higher deduction (refer Notes 1 to 9) | AB | CHAR | 1 | O | `reason_code` | If applicable quote value (code) as per Annexure 6 else no value to be provided. |
| 33 | Certificate number(s) of the certificate under section 395(1) / 395(2) issued for non-deduction /lower deduction | AC | CHAR | 15 | O | `certificate_no` | Mandatory to mention 10 or 15 digit alphanumeric value if, "A" is mentioned in field no. 32 (Remark field). |
| 34 | Filler 1 | – | NA | 0 | NA | - |  |
| 35 | Filler 2 | – | NA | 0 | NA | - |  |
| 36 | Filler 3 | – | NA | 0 | NA | - |  |
| 37 | Address in Country of Residence | F | CHAR | 150 | O | `address_abroad` | Address in country of residence This field will be mandatory only in case of below conditions are satisfied. a. if rate of deduction is less than 20% b. remark value as 'C' c. PAN of the deductee is not available (i.e. 'PANNOTAVBL', 'PANAPPLIED' or 'PANINVALID'). d. Value under field no. 16 above (i.e. Nature of remittances) is 16,27, 49, 21, 52 & 31 (Please refer Annexure 9 below). Mention the address of the deductee. Only special characters are not allowed under this field. |
| 38 | Email ID | G | CHAR | 75 | O | `email` | 1. Email format must be checked -atleast @ and '.' should be mentioned. 2. Both @ and '.' shouldbe preceded and suceeded by atleast one character. 3. At least one '.' should come after '@'. 4.Special characters like *, # ,$, &,_, etc. are allowed for email id. The special characters should be preceeded/subceeded by either @ and/or dot. This field will be mandatory only in case of below conditions are satisfied. a. if rate of deduction is less than 20% b. remark value as 'C' c. PAN of the deductee is not available (i.e. 'PANNOTAVBL', 'PANAPPLIED' or 'PANINVALID'). d. Value under field no. 16 above (i.e. Nature of remittances) is 16,27, 49, 21, 52 & 31 (Please refer Annexure 9 below). e. Value under field no. 36 above (i.e. Nature of remittances) is 05, 06, 07, 10, 11, 12, 13, 14, 16 or 17 (Please refer Annexure 9 below). Mention the address of the deductee. Only special characters are not allowed under this field. |
| 39 | Contact Number (ISD Code,land line or mob) | H | INTEGER | 15 | O | `phone` | Country calling code for deductor contact number (e.g., 91 for India). Deductor contact number without country code; digits only. Max 15. This field will be mandatory only in case of below conditions are satisfied. a. if rate of deduction is less than 20% b. remark value as 'C' c. PAN of the deductee is not available (i.e. 'PANNOTAVBL', 'PANAPPLIED' or 'PANINVALID'). d. Value under field no. 16 above (i.e. Nature of remittances) is 16,27, 49, 21, 52 & 31 (Please refer Annexure 8 below). Value in this field is applicable for statements pertaining to FY 2016-17 onwards. No value to be provided for statements pertaining prior to FY 2016-17. e. Value under field no. 36 above (i.e. Nature of remittances) is 05, 06, 07, 10, 11, 12, 13, 14, 16 or 17 (Please refer Annexure 9 below). Mention the address of the deductee. Only special characters are not allowed under this field. |
| 40 | Filler 7 | – | NA | 0 | O | - | No value should be specified |
| 41 | Tax Identification Number/Unique Identification Number issued by the country of Residence | E | CHAR | 25 | O | `tin` | Value to be specified as per country of residence This field will be mandatory only in case of below conditions are satisfied. a. if rate of deduction is less than 20% b. remark value as 'C' c. PAN of the deductee is not available (i.e. 'PANNOTAVBL', 'PANAPPLIED' or 'PANINVALID'). d. Value under field no. 16 above (i.e. Nature of remittances) is 16,27, 49, 21, 52 & 31 (Please refer Annexure 8 below). Value in this field is applicable for statements pertaining to FY 2016-17 onwards. No value to be provided for statements pertaining prior to FY 2016-17. e. Value under field no. 36 above (i.e. Nature of remittances) is 05, 06, 07, 10, 11, 12, 13, 14, 16 or 17 (Please refer Annexure 9 below). Mention the address of the deductee. Only special characters are not allowed under this field. Tax Identification Number of the deductee in the country or specified territory of his residence and in case no such number is available, then a unique number on the basis of which the deductee is identified by the Government of that country or the specified territory of which he claims to be a resident. Only zero's or special characters or only spaces are not allowed under this field. |
| 42 | Last Total Tax Deposited ( Used for Verification) (Not applicable) | – | NA | 0 | O | - | No value should be specified |
| 43 | Filler 10 | – | NA | 0 | O | - | No value should be specified |
| 44 | Filler 11 | – | NA | 0 | O | - | No value should be specified |
| 45 | Record Hash (Not applicable) | – | NA | 0 | O | - | No value should be specified |

## The ten figures that come from `meta.non_resident`

Ten fields of the deductee record ask about the non-resident rather than the payment: the deductee's status (field 12), whether it has opted out of the taxation regime under section 202(1) (field 14), the nature of the remittance (field 16), the country it is sent to (field 17), whether the amount is grossed up (field 21), whether the rate follows the Act or a treaty (field 30), and the deductee's address, email, contact number and tax identification number (fields 37, 38, 39 and 41). All ten were fillers or "not applicable" on Form 140. The statement document is shared with Form 140 and has no place for any of them, so they travel in `meta.non_resident`, an object keyed by the deductee's PAN in capitals:

```json
"meta": {
  "non_resident": {
    "AACCZ4321R": {
      "status": "1",
      "opting_out": "N",
      "nature_of_remittance": "27",
      "country_code": "175",
      "grossed_up": "N",
      "rate_basis": "A",
      "address_abroad": "HOOFDWEG 12, 1096 AC AMSTERDAM",
      "email": "tax@zuiderzee.example",
      "phone": "31201234567",
      "tin": "NL812345678B01"
    }
  }
}
```

| Key | DD field | Workbook row | Required |
|---|---:|---:|---|
| `status` | 12 | 165 | Every row. Code from Annexure 8, for example 1 for a company, 2 for an individual. |
| `opting_out` | 14 | 167 | Every row. Y or N. |
| `nature_of_remittance` | 16 | 169 | Rows whose section code appears in Annexure 9 (T-FV-6544). |
| `country_code` | 17 | 170 | Every row (T-FV-6425). Code from Annexure 10. |
| `grossed_up` | 21 | 174 | Every row. Y or N (T-FV-6429). |
| `rate_basis` | 30 | 183 | Every row. A for the Income-tax Act, B for a treaty. |
| `address_abroad` | 37 | 190 | See the four conditions below. |
| `email` | 38 | 191 | Same conditions as field 37. |
| `phone` | 39 | 192 | Same conditions as field 37. |
| `tin` | 41 | 194 | Same conditions as field 37. |

Fields 37 to 41 are mandatory when all four of these hold: the rate of deduction is below 20 per cent, the reason flag is C, the deductee's PAN is a placeholder (PANAPPLIED, PANINVALID or PANNOTAVBL), and the nature of remittance is 16, 27, 49, 21, 52 or 31. The workbook names no other list, and the list of natures for which the utility refuses these fields is compiled into the utility itself (T-FV-4340 to T-FV-4343), so the module writes what the document gives and leaves that check to the upload.

The rules the module applies:

* Nothing is defaulted. A key the block does not carry is written as a blank field. A plausible-looking N in a field the document never answered is a wrong statement, while a blank field draws a message from the utility that names the field.
* `opting_out`, `grossed_up` and `rate_basis` are trimmed to one character and upper-cased, so " n " becomes N and "b" becomes B. The rate in field 28 is written with four decimals.
* A malformed block stops the build with an error naming it. `meta.non_resident` has to be an object keyed by PAN, each value has to be an object, and a key that is not one of the ten is refused. A typo such as `staus` would otherwise drop a status under a name nothing reads, and the file would go to the portal missing a figure the utility requires.
* Keys are the PAN with spaces stripped and letters upper-cased. Two deductees who share a placeholder PAN therefore share one block, so a statement that uses a placeholder for two different people cannot give them different lists. Real PANs do not collide.

## Where Form 144 differs from Form 140

The two workbooks were compared cell by cell. Both carry 18, 72, 30 and 45 fields in the same order, and the table below is every field whose text differs, including wording changes that mean nothing in practice. The changes that matter when reading a statement are listed after it.

| Record | Field | What differs |
|---|---:|---|
| FH | 3 | remark reworded |
| BH | 5 | remark reworded |
| BH | 9 | name: "Token no. of previous regular statement (Form no. 140)." → "Token no. of previous regular statement (Form no. 144)."; remark reworded |
| BH | 10 | name: "Token Number of the statement submitted - (Not applicable)" → "Token Number of the statement submitted -- (Not applicable)" |
| BH | 16 | remark reworded |
| BH | 17 | form column: NA → – |
| BH | 31 | form column: – → NA; type: CHAR → NA; remark reworded |
| BH | 39 | name: "Responsible Person's Address5 (District)" → "Responsible Person's Address5(District)" |
| BH | 44 | name: "Responsible Person Contact Country/Region" → "Responsible Person Contact Country Code"; form column: NA → – |
| BH | 45 | form column: NA → –; remark reworded |
| BH | 52 | name: "Whether regular statement for Form 140 filed for earlier period" → "Whether regular statement for Form 144 filed for earlier period"; remark reworded |
| BH | 68 | remark reworded |
| CD | 8 | remark reworded |
| CD | 13 | remark reworded |
| CD | 17 | remark reworded |
| CD | 19 | name: "Date of 'Bank Challan / Transfer Voucher' (DDMMYYYY)" → "Date of 'Bank Challan / DDO Serial Number' (DDMMYYYY)" |
| CD | 21 | name: "Total Tax Deposited Amount as per Collectee annexure (Total Sum of column no. L) for the specified challan" → "Total Tax Deposited Amount as per Deductee annexure (Total Sum of column no. U) for the specified challan" |
| CD | 22 | name: "Total Tax Deducted Amount as per Deductor annexure (Total sum of Column no. J) for the specified challan" → "Total Tax Deducted Amount as per Deductee annexure (Total sum of Column no. S) for the specified challan"; remark reworded |
| CD | 23 | remark reworded |
| CD | 25 | name: "Other Allocation" → "Others Allocation" |
| DD | 4 | remark reworded |
| DD | 8 | remark reworded |
| DD | 12 | name: "Remarks 3 (for future use)" → "Status"; form column: – → I; type: NA → INTEGER; size: 0 → 2; M/O: O → M; remark reworded |
| DD | 14 | name: "Remarks 5 (for future use)" → "Whether deductee opting out of taxation regime u/s 202(1)"; form column: – → M; type: NA → CHAR; size: 0 → 1; M/O: O → M; remark reworded |
| DD | 15 | form column: E → J |
| DD | 16 | name: "Remarks 6 (for future use)" → "Nature of Remittance"; form column: – → K; type: NA → INTEGER; size: 0 → 2; remark reworded |
| DD | 17 | name: "Remarks 7 (for future use)" → "Country to which remittance is made"; form column: – → L; type: NA → INTEGER; size: 0 → 3; M/O: O → M; remark reworded |
| DD | 18 | name: "Whether the total amount of tax deducted as mentioned in Column (J) has been deposited (Yes/No)" → "Whether the total amount of tax deducted as mentioned in Column (S) has been deposited (Yes/No)"; form column: K → T |
| DD | 19 | form column: F → N |
| DD | 20 | form column: G → O |
| DD | 21 | name: "Grossing up Indicator (Not applicable)" → "Whether the amount paid or credited is grossed up as per section 393(10)"; form column: – → P; type: NA → CHAR; size: 0 → 1; M/O: O → M; remark reworded |
| DD | 22 | name: "Amount of cash withdrawal in excess of Rs. 1 crore as referred to in section 393(3) [Table: Sl. No. 5] (in case of person other than cooperative society)" → "Amount of cash withdrawal in excess of Rs. 1 crore as referred to in section 393(3) [Table: Sl. No. 5] (in case of person other than co- operative society)"; form column: H → Q |
| DD | 23 | form column: I → R |
| DD | 24 | form column: J → S; remark reworded |
| DD | 25 | form column: L → U; remark reworded |
| DD | 27 | form column: N → V |
| DD | 28 | form column: M → W; remark reworded |
| DD | 30 | name: "Remarks 10 (for future use)" → "Whether rate of TDS is as per IT Act (a) or DTAA (b)"; form column: – → Z; type: NA → CHAR; size: 0 → 1; M/O: O → M; remark reworded |
| DD | 31 | name: "Unique Identification Number of Form No. 121 submitted by the deductee" → "Unique acknowledgement number of the corresponding Form No. 15CA [FN 144], if applicable"; form column: Q → AA; remark reworded |
| DD | 32 | name: "Reason for non-deduction / Lower deduction / Higher deduction / Threshold / Transporter etc." → "Reason for non-deduction /lower deduction/higher deduction (refer Notes 1 to 9)"; form column: O → AB; remark reworded |
| DD | 33 | name: "Certificate number of certificate issued under section 395 for non-deduction /lower deduction" → "Certificate number(s) of the certificate under section 395(1) / 395(2) issued for non-deduction /lower deduction"; form column: P → AC |
| DD | 34 | type: NA → –; size: 0 → –; M/O: O → –; remark dropped |
| DD | 35 | type: NA → –; size: 0 → –; M/O: O → –; remark dropped |
| DD | 36 | type: NA → –; size: 0 → –; M/O: O → –; remark dropped |
| DD | 37 | name: "Filler 4" → "Address in Country of Residence"; form column: – → F; type: NA → CHAR; size: 0 → 150; remark reworded |
| DD | 38 | name: "Filler 5" → "Email ID"; form column: – → G; type: NA → CHAR; size: 0 → 75; remark reworded |
| DD | 39 | name: "Filler 6" → "Contact Number (ISD Code,land line or mob)"; form column: – → H; type: NA → INTEGER; size: 0 → 15; remark reworded |
| DD | 41 | name: "Filler 8" → "Tax Identification Number/Unique Identification Number issued by the country of Residence"; form column: – → E; type: NA → CHAR; size: 0 → 25; remark reworded |

* Fields 12, 14, 16, 17, 21, 30, 37, 38, 39 and 41 stop being fillers and become the ten figures above. Field 12 is the only one of the ten that also gains a type and a size (INTEGER, 2).
* Field 31 keeps a remark about "Unique Identification Number of Form No. 121", which is the Form 140 field it replaces, but its name on Form 144 is the Form 15CA acknowledgement number, 26 characters. The module writes the row's `form121` attribute there, so on a Form 144 document that attribute should hold the 15CA acknowledgement.
* Field 25's remark is the challan record's remark about the fee allocation copied onto a deductee row. It cannot apply there. The module follows Form 140, where field 25 is the row's own deposited tax, and the deposit arithmetic in the toolkit uses that reading.
* CD field 13 and DD fields 24, 25 and 28 drop sections 1034 and 1038 from the list of codes with special treatment; those two codes exist on Form 140 only, and Form 144's own zero-value rule covers 1059 and 1061.
* BH field 16's example still reads assessment year 2008-09. The rule is that the assessment year is the year after the financial year, so tax year 2026-27 takes 202728. The module writes the value from the document.
* CD field 19's name mentions the DDO serial number; the field still holds a date (ddmmyyyy), and the module writes the challan date.
* The form number in BH field 5 is 144. The FH file type stays NS1, and T-FV-2065 accepts an NS1 file whose batch header says 140 or 144.
* Section codes come from Form 144's own Annexure 2 and reason flags from its own Annexure 6, both below.

## Form 144's annexures

The two forms share Annexures 1, 3, 4 and 5 (state codes, ministry codes, deductor categories and the state list again). Comparing those blocks between the two workbooks cell by cell found the same content, so they are not repeated here. What follows is the six annexures that are Form 144's own.

### Annexure 2 - section codes (DD field 15)

Thirty codes. Code 1004 is shared with Form 140; 1039 to 1067 are Form 144's own. The overlap between the two forms is 1004 and 1058 to 1067, eleven codes. `assets/annexures_144.json` carries this table, extracted from this workbook by `extract_annexures.py --form144`, and `tds lint` reads it for a Form 144 document, so a section code outside the thirty is reported.

| Code | Section | Nature of payment |
|---:|---|---|
| 1004 | 392(7) | Any payment of accumulated balance due to an employee |
| 1039 | 393(2) [Table: Sl. No. 1] | Any income referred to in section 211. |
| 1040 | 393(2) [Table: Sl. No. 2] | Any income by way of interest payable in respect of monies borrowed in foreign currency from a source outside India,— (a) under a loan agreement or issue of long term infrastructure bond on or after the 1st July, 2012 but before the 1st July, 2023; or (b) by way of issue of any long-term bond on or after the 1st October, 2014 but before the 1st July, 2023, which is approved by the Central Government in this behalf. |
| 1041 | 393(2) [Table: Sl. No. 3] | Any income by way of interest payable in respect of monies borrowed from a source outside India by way of issue of rupee denominated bond before the 1st July, 2023. |
| 1042 | 393(2) [Table: Sl. No. 4.E(a)] | Any income by way of interest payable in respect of monies borrowed from a source outside India by way of issue of any long-term bond or rupee denominated bond, which is listed only on a recognised stock exchange located in any International Financial Services Centre. - Issued on or after the 1st April, 2020 but before the 1st July, 2023 |
| 1043 | 393(2) [Table: Sl. No. 4.E(b)] | Any income by way of interest payable in respect of monies borrowed from a source outside India by way of issue of any long-term bond or rupee denominated bond, which is listed only on a recognised stock exchange located in any International Financial Services Centre - Issued on or after the 1st July, 2023. |
| 1044 | 393(2) [Table: Sl. No. 5] | Income by way of Interest from Infrastructure debt fund payable to a Non-Resident |
| 1045 | 393(2) [Table: Sl. No.6.E(a)] | Any distributed income referred to in section 223, being of the nature referred to in Schedule V [Table: Sl. No. 3.B(a)] |
| 1046 | 393(2) [Table: Sl. No.6.E(b)] | Any distributed income referred to in section 223, being of the nature referred to in Schedule V [Table: Sl. No. 3.B(b)] |
| 1047 | 393(2) [Table: Sl. No. 7] | Any distributed income referred to in section 223, being of the nature referred to in Schedule V [Table: Sl. No. 4]. |
| 1048 | 393(2) [Table: Sl. No. 8] | Any income, other than that proportion of income which is exempt under Schedule V [Table: Sl. No. 2], in respect of units of an investment fund specified in section 224. |
| 1049 | 393(2) [Table: Sl. No. 9] | Any income in respect of an investment in a securitisation trust specified in section 221. |
| 1050 | 393(2) [Table: Sl. No. 10] | Any income— (a) in respect of units of a Mutual Fund specified under Schedule VII [Table: Sl. No. 20] or [Table: Sl. No. 21]; or (b) from the specified company. |
| 1051 | 393(2) [Table: Sl. No. 11] | Any income in respect of units referred to in section 208. |
| 1052 | 393(2) [Table: Sl. No. 12] | Any income by way of long-term capital gains arising from the transfer of units referred to in section 208. |
| 1053 | 393(2) [Table: Sl. No. 13] | Any income by way of interest or dividends in respect of bonds or Global Depository Receipts referred to in section 209. |
| 1054 | 393(2) [Table: Sl. No. 14] | Any income by way of long-term capital gains arising from the transfer of bonds or Global Depository Receipts referred to in section 209. |
| 1055 | 393(2) [Table: Sl. No. 15] | Any income in respect of securities referred to in section 210(1) [Table: Sl. No. 1]. |
| 1056 | 393(2) [Table: Sl. No. 16] | Any income in respect of securities referred to in section 210(1) [Table: Sl. No. 1]. |
| 1057 | 393(2) [Table: Sl. No. 17] | Any interest (not being interest referred to against serial numbers 2, 3, 4 and 5) or any other sum chargeable under the provisions of this Act, not being income chargeable under the head “Salaries”. |
| 1058 | 393(3) [Table: Sl. No. 1] | Any income by way of winnings (other than winnings from Sl. No. 2 of the table at section 393(3)) from–– (a) any lottery; or (b) crossword puzzle; or (c) card game and other game of any sort; or (d) gambling or betting of any form or nature whatsoever |
| 1059 | 393(3) [Table: Sl. No. 1] Note 2 | Any income by way of winnings (other than winnings from Sl. No. 2 of the table at section 393(3)) from–– (a) any lottery; or (b) crossword puzzle; or (c) card game and other game of any sort; or (d) gambling or betting of any form or nature whatsoever where consideration, is made in kind or cash is not sufficient to meet the tax liability and tax has been paid before such winnings are released |
| 1060 | 393(3) [Table: Sl. No. 2] | Any income by way of winnings from online game. |
| 1061 | 393(3) [Table: Sl. No. 2] Note 2 | Any income by way of winnings from online games, is made in kind or cash is not sufficient to meet the tax liability and tax has been paid before such winnings are released |
| 1062 | 393(3) [Table: Sl. No. 3] | Any income by way of winnings from any horse race. |
| 1063 | 393(3) [Table: Sl. No. 4] | Any income, credited or paid to a person, who is or has been stocking, distributing, purchasing or selling lottery tickets, by way of commission, remuneration or prize (by whatever name called) on such tickets |
| 1064 | 393(3) [Table: Sl. No. 5.D(a)] | Payment of certain amounts in cash by bank/ post office / co-operative society to a deductee being a co-operative society |
| 1065 | 393(3) [Table: Sl. No. 5.D(b)] | Payment of certain amounts in cash by bank/ post office / co-operative society to a deductee being a person other than co-operative society |
| 1066 | 393(3) [Table: Sl. No. 6] | Any amount referred to in section 80CCA(2)(a) of the Income-tax Act, 1961 (43 of 1961). |
| 1067 | 393(3) [Table: Sl. No. 7] | Any sum in the nature of salary, remuneration, commission, bonus or interest paid to a partner of the firm or credited to his account (including capital account). |

### Annexure 6 - reason flags (DD field 32)

One row per flag and section code, so a code that accepts several flags appears several times. Flag A is a certificate for nil or lower deduction under section 395(1) or 395(2); flag C is a higher rate under section 397(2) for want of a PAN; G, H, I, N, O, Y and Z are reserved for particular codes. The utility checks the flag against the section (T-FV-6447) and, where the flag is A, requires the certificate number in field 33 (T-FV-6454).

| Flag | Section | Code | Note |
|---|---|---:|---|
| A | 392(7) | 1004 | Flag A - “Lower deduction” or “no deduction” is on account of a certificate under section 395(1) and 395(2) |
| A | 393(2) [Table: Sl. No. 1] | 1039 |  |
| A | 393(2) [Table: Sl. No. 2] | 1040 |  |
| A | 393(2) [Table: Sl. No. 3] | 1041 |  |
| A | 393(2) [Table: Sl. No. 4.E(a)] | 1042 |  |
| A | 393(2) [Table: Sl. No. 4.E(b)] | 1043 |  |
| A | 393(2) [Table: Sl. No. 5] | 1044 |  |
| A | 393(2) [Table: Sl. No.6.E(a)] | 1045 |  |
| A | 393(2) [Table: Sl. No.6.E(b)] | 1046 |  |
| A | 393(2) [Table: Sl. No. 7] | 1047 |  |
| A | 393(2) [Table: Sl. No. 8] | 1048 |  |
| A | 393(2) [Table: Sl. No. 9] | 1049 |  |
| A | 393(2) [Table: Sl. No. 10] | 1050 |  |
| A | 393(2) [Table: Sl. No. 11] | 1051 |  |
| A | 393(2) [Table: Sl. No. 12] | 1052 |  |
| A | 393(2) [Table: Sl. No. 13] | 1053 |  |
| A | 393(2) [Table: Sl. No. 14] | 1054 |  |
| A | 393(2) [Table: Sl. No. 15] | 1055 |  |
| A | 393(2) [Table: Sl. No. 16] | 1056 |  |
| A | 393(2) [Table: Sl. No. 17] | 1057 |  |
| A | 393(3) [Table: Sl. No. 1] | 1058 |  |
| A | 393(3) [Table: Sl. No. 2] | 1060 |  |
| A | 393(3) [Table: Sl. No. 3] | 1062 |  |
| A | 393(3) [Table: Sl. No. 4] | 1063 |  |
| A | 393(3) [Table: Sl. No. 5.D(a)] | 1064 |  |
| A | 393(3) [Table: Sl. No. 5.D(b)] | 1065 |  |
| A | 393(3) [Table: Sl. No. 6] | 1066 |  |
| A | 393(3) [Table: Sl. No. 7] | 1067 |  |
| C | 392(7) | 1004 | Deduction is on higher rate under section 397(2) on account of non-furnishing of PAN |
| C | 393(2) [Table: Sl. No. 1] | 1039 |  |
| C | 393(2) [Table: Sl. No. 2] | 1040 |  |
| C | 393(2) [Table: Sl. No. 3] | 1041 |  |
| C | 393(2) [Table: Sl. No. 4.E(a)] | 1042 |  |
| C | 393(2) [Table: Sl. No. 4.E(b)] | 1043 |  |
| C | 393(2) [Table: Sl. No. 5] | 1044 |  |
| C | 393(2) [Table: Sl. No.6.E(a)] | 1045 |  |
| C | 393(2) [Table: Sl. No.6.E(b)] | 1046 |  |
| C | 393(2) [Table: Sl. No. 7] | 1047 |  |
| C | 393(2) [Table: Sl. No. 8] | 1048 |  |
| C | 393(2) [Table: Sl. No. 9] | 1049 |  |
| C | 393(2) [Table: Sl. No. 10] | 1050 |  |
| C | 393(2) [Table: Sl. No. 11] | 1051 |  |
| C | 393(2) [Table: Sl. No. 12] | 1052 |  |
| C | 393(2) [Table: Sl. No. 13] | 1053 |  |
| C | 393(2) [Table: Sl. No. 14] | 1054 |  |
| C | 393(2) [Table: Sl. No. 15] | 1055 |  |
| C | 393(2) [Table: Sl. No. 16] | 1056 |  |
| C | 393(2) [Table: Sl. No. 17] | 1057 |  |
| C | 393(3) [Table: Sl. No. 1] | 1058 |  |
| C | 393(3) [Table: Sl. No. 2] | 1060 |  |
| C | 393(3) [Table: Sl. No. 3] | 1062 |  |
| C | 393(3) [Table: Sl. No. 4] | 1063 |  |
| C | 393(3) [Table: Sl. No. 5.D(a)] | 1064 |  |
| C | 393(3) [Table: Sl. No. 5.D(b)] | 1065 |  |
| C | 393(3) [Table: Sl. No. 6] | 1066 |  |
| C | 393(3) [Table: Sl. No. 7] | 1067 |  |
| G | 393(2) [Table: Sl. No. 17] | 1057 | No deduction is made on interest paid by an Offshore Banking Unit as per the provisions of section 393(8) |
| H | 393(2) [Table: Sl. No. 16] | 1056 | No deduction is in view of section 393(4) [Table: Sl. No. 17] in respect of an income paid to a specified fund which is exempt as per Schedule VI [Table: Sl. Nos. 1 to 4] |
| I | 393(2) [Table: Sl. No. 15] | 1055 | No deduction is in view of section 393(4) [Table: Sl. No. 16] in respect of income of the nature of capital gains on transfer of securities referred to in section 210 paid or payable to a Foreign Institutional Investor |
| N | 393(3) [Table: Sl. No. 5.D(a)] | 1064 | No deduction is on account of payment made to a person referred to in section 393(4) [Table: Sl. No. 18] of the Act or on account of notification issued under fifth proviso to section 194N of the Income-tax Act, 1961 |
| N | 393(3) [Table: Sl. No. 5.D(b)] | 1065 |  |
| O | 393(2) [Table: Sl. No.6.E(b)] | 1046 | Any distributed income referred to in section 223, being of the nature referred to in Schedule V [Table: Sl. No. 3.B(b)] |
| Y | 392(7) | 1004 | No deduction is on account of payment below threshold limit as specified in the Income-tax Act, 2025 |
| Y | 393(3) [Table: Sl. No. 1] | 1058 |  |
| Y | 393(3) [Table: Sl. No. 1] Note 2 | 1059 |  |
| Y | 393(3) [Table: Sl. No. 3] | 1062 |  |
| Y | 393(3) [Table: Sl. No. 4] | 1063 |  |
| Y | 393(3) [Table: Sl. No. 6] | 1066 |  |
| Y | 393(3) [Table: Sl. No. 7] | 1067 |  |
| Z | 393(2) [Table: Sl. No. 17] | 1057 | No deduction or lower deduction is on account of payment in view of notification issued under section 400(1) of the Act |

### Annexure 7 - minor head codes (CD field 23)

| Code | Particulars |
|---:|---|
| 200 | TDS payable by taxpayer |
| 400 | TDS regular assessment (Raised by I. T, Dept.) |
| 100 | Advance Tax |

### Annexure 8 - status of the deductee (DD field 12)

| Code | Status |
|---:|---|
| 1 | Company |
| 2 | Individual |
| 3 | Hindu undivided family |
| 4 | Association of Persons (AOP) except in case of AOP consisting of only companies as its members |
| 5 | Association of Persons (AOP) consisting of only companies as its members |
| 6 | Co-operative society |
| 7 | Firm |
| 8 | Body of individuals |
| 9 | Artificial juridical person referred to in clause (g) of sub-section (77) of section 2 of the Income-tax Act, 2025 |
| 10 | Others |

### Annexure 9 - nature of remittance (DD field 16)

The nature codes allowed for each section. The workbook merges the section column over each block, so the code is written once and belongs to every row under it; the table below repeats it on each row. A row whose section code is here has to carry its nature (T-FV-6544); a row whose section is not here leaves the field blank. Several natures usually appear against one section, so the table lists pairs.

| Code | Nature of remittance | Section code |
|---:|---|---:|
| 27 | Interest income | 1040 |
| 27 | Interest income | 1041 |
| 27 | Interest income | 1042 |
| 27 | Interest income | 1043 |
| 27 | Interest income | 1044 |
| 27 | Interest income | 1045 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1046 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1046 |
| 27 | Interest income | 1048 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1048 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1048 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1048 |
| 67 | Long term capital gains referred to in section 197(1) | 1048 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1048 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1048 |
| 70 | Short term capital gains referred to in section 196 | 1048 |
| 27 | Interest income | 1049 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1049 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1049 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1049 |
| 67 | Long term capital gains referred to in section 197(1) | 1049 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1049 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1049 |
| 70 | Short term capital gains referred to in section 196 | 1049 |
| 27 | Interest income | 1050 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1050 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1050 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1050 |
| 67 | Long term capital gains referred to in section 197(1) | 1050 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1050 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1050 |
| 70 | Short term capital gains referred to in section 196 | 1050 |
| 27 | Interest income | 1051 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1051 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1051 |
| 71 | Long Term Capital Gains arising from transfer Transfer of Units reffered to in Section 208 | 1052 |
| 27 | Interest income | 1053 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1053 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1053 |
| 72 | Long-term capital gains arising from the transfer of bonds or Global Depository Receipts referred to in section 209 | 1054 |
| 27 | Interest income | 1055 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1055 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1055 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1055 |
| 67 | Long term capital gains referred to in section 197(1) | 1055 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1055 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1055 |
| 70 | Short term capital gains referred to in section 196 | 1055 |
| 27 | Interest income | 1056 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1056 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1056 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1056 |
| 67 | Long term capital gains referred to in section 197(1) | 1056 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1056 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1056 |
| 70 | Short term capital gains referred to in section 196 | 1056 |
| 27 | Interest income | 1057 |
| 73 | Dividend income referred to in the in the section 207(1) [Table: Sl. No.1] | 1057 |
| 16 | Dividend income referred to in the section 207(1) [Table: Sl. No.2] | 1057 |
| 28 | Investment income | 1057 |
| 66 | Long term capital gains referred to in section 214 [Table: Sl. No. 2] | 1057 |
| 67 | Long term capital gains referred to in section 197(1) | 1057 |
| 68 | LTCG other than those specifically listed under Schedule II, Sl. No. 14 and Sl. No. 17 [related to section 10(36) of IT ACT-1961] | 1057 |
| 69 | Long term capital gains referred to in section 198 exceeding one lakh twenty-five thousand rupees, | 1057 |
| 70 | Short term capital gains referred to in section 196 | 1057 |
| 21 | Fees for Technical Services/ Fees for included services where the agreement is made after the 31st March, 1976 | 1057 |
| 74 | Fees for Technical Services/ Fees for included services where the agreement is made after the 29th February, 1964 but before the 1st April, 1976 | 1057 |
| 49 | Royalty where the agreement is made after the 31st March, 1976 | 1057 |
| 75 | Royalty where the agreement is made after the 31st March, 1961 but before the 1st April, 1976 | 1057 |
| 99 | Other income | 1057 |

### Annexure 10 - country codes (DD field 17)

The codes are the workbook's own strings, two characters below 100 with a leading zero ('04' for Algeria), and the field is declared INTEGER size 3. The department's sample statement writes the padded form, and the module writes the value the document gives without padding it.

| Code | Country |
|---:|---|
| 01 | AFGHANISTAN |
| 02 | AKROTIRI |
| 03 | ALBANIA |
| 04 | ALGERIA |
| 05 | AMERICAN SAMOA |
| 06 | ANDORRA |
| 07 | ANGOLA |
| 08 | ANGUILLA |
| 09 | ANTARCTICA |
| 10 | ANTIGUA AND BARBUDA |
| 11 | ARGENTINA |
| 12 | ARMENIA |
| 13 | ARUBA |
| 14 | ASHMORE AND CARTIER ISLANDS |
| 15 | AUSTRALIA |
| 16 | AUSTRIA |
| 17 | AZERBAIJAN |
| 18 | BAHRAIN |
| 19 | BAILIWICK OF GUERNSEY |
| 20 | BAILIWICK OF JERSEY |
| 21 | BAKER ISLAND |
| 22 | BANGLADESH |
| 23 | BARBADOS |
| 24 | BELARUS |
| 25 | BELGIUM |
| 26 | BELIZE |
| 27 | BENIN PORTO |
| 28 | BERMUDA |
| 29 | BHUTAN |
| 30 | BOLIVIA |
| 31 | BOSNIAAND HERZEGOVINA |
| 32 | BOTSWANA |
| 33 | BOUVET ISLAND |
| 34 | BRAZIL |
| 35 | BRITISH INDIAN OCEAN TERRITORY |
| 36 | BRUNEI |
| 37 | BULGARIA |
| 38 | BURKINA FASO |
| 39 | BURUNDI |
| 40 | CAMBODIA |
| 41 | CAMEROON |
| 42 | CANADA |
| 43 | CAPE VERDE |
| 44 | CAYMAN ISLANDS |
| 45 | CENTRAL AFRICAN REPUBLIC |
| 46 | CHAD |
| 47 | CHILE |
| 48 | CHINA |
| 49 | CHRISTMAS ISLAND |
| 50 | CLIPPERTON ISLAND |
| 51 | COCOS (KEELING) ISLANDS |
| 52 | COLOMBIA |
| 53 | COMMONWEALTH OF PUERTO RICO |
| 54 | COMMONWEALTH OF THE NORTHERN MARIANA ISLANDS |
| 55 | COMOROS |
| 56 | CONGO,DEMOCRATIC REPUBLIC OF THE |
| 57 | CONGO,REPUBLIC OF THE |
| 58 | COOK ISLANDS |
| 59 | CORAL SEA ISLANDS |
| 60 | CORAL SEA ISLANDS TERRITORY |
| 61 | COSTA RICA |
| 62 | COTE D'IVOIRE |
| 63 | CROATIA |
| 64 | CUBA |
| 65 | CYPRUS |
| 66 | CZECH REPUBLIC |
| 67 | DENMARK |
| 68 | DEPARTMENTAL COLLECTIVITY OF MAYOTTE |
| 69 | DHEKELIA |
| 70 | DJIBOUTI |
| 71 | DOMINICA |
| 72 | DOMINICAN REPUBLIC |
| 73 | EAST TIMOR (TIMORLASTE) |
| 74 | ECUADOR |
| 75 | EGYPT |
| 76 | ELSALVADOR |
| 77 | EQUATORIAL GUINEA |
| 78 | ERITREA |
| 79 | ESTONIA |
| 80 | ETHIOPIA |
| 81 | FALKLAND ISLANDS (ISLAS MALVINAS) |
| 82 | FAROE ISLANDS |
| 83 | FIJI |
| 84 | FINLAND |
| 85 | FRANCE |
| 86 | FRENCH GUIANA |
| 87 | FRENCH POLYNESIA |
| 88 | FRENCH SOUTHERN ISLANDS |
| 89 | GABON |
| 90 | GEORGIA |
| 91 | GERMANY |
| 92 | GEURNSEY |
| 93 | GHANA |
| 94 | GIBRALTAR |
| 95 | GREECE |
| 96 | GREENLAND |
| 97 | GRENADA |
| 98 | GUADELOUPE |
| 100 | GUAM |
| 101 | GUATEMALA |
| 102 | GUERNSEY |
| 103 | GUINEA |
| 104 | GUINEABISSAU |
| 105 | GUYANA |
| 106 | HAITI |
| 107 | HEARD ISLAND AND MCDONALD ISLANDS |
| 108 | HONDURAS |
| 109 | HONG KONG |
| 110 | HOWLAND ISLAND |
| 111 | HUNGARY |
| 112 | ICELAND |
| 113 | INDIA |
| 114 | INDONESIA |
| 115 | IRAN |
| 116 | IRAQ |
| 117 | IRELAND |
| 118 | ISLE OF MAN |
| 119 | ISRAEL |
| 120 | ITALY |
| 121 | JAMAICA |
| 122 | JAN MAYEN |
| 123 | JAPAN |
| 124 | JARVIS ISLAND |
| 125 | JERSEY |
| 126 | JOHNSTON ATOLL |
| 127 | JORDAN |
| 128 | KAZAKHSTAN |
| 129 | KENYA |
| 130 | KINGMAN REEF |
| 131 | KIRIBATI |
| 132 | KOREA, NORTH |
| 133 | KOREA, SOUTH |
| 134 | KOSOVO |
| 135 | KUWAIT |
| 136 | KYRGYZSTAN |
| 137 | LAOS |
| 138 | LATVIA |
| 139 | LEBANON |
| 140 | LESOTHO |
| 141 | LIBERIA |
| 142 | LIBYA |
| 143 | LIECHTENSTEIN |
| 144 | LITHUANIA |
| 145 | LUXEMBOURG |
| 146 | MACAU |
| 147 | MACEDONIA |
| 148 | MADAGASCAR |
| 149 | MALAWI |
| 150 | MALAYSIA |
| 151 | MALAYSIA (LABUAN) |
| 152 | MALDIVES |
| 153 | MALI |
| 154 | MALTA |
| 155 | MARSHALLISLANDS |
| 156 | MARTINIQUE |
| 157 | MAURITANIA |
| 158 | MAURITIUS |
| 159 | MAYOTTE |
| 160 | UNITED MEXICAN STATES |
| 161 | MICRONESIA, FEDERATED STATES OF |
| 162 | MIDWAY ISLANDS |
| 163 | MOLDOVA |
| 164 | MONACO |
| 165 | MONGOLIA |
| 166 | MONTENEGRO |
| 167 | MONTSERRAT |
| 168 | MOROCCO |
| 169 | MOZAMBIQUE |
| 170 | MYANMAR (BURMA) |
| 171 | NAMIBIA |
| 172 | NAURU |
| 173 | NAVASSA ISLAND |
| 174 | NEPAL |
| 175 | NETHERLANDS |
| 176 | NETHERLANDS ANTILLES |
| 177 | NEW CALEDONIA |
| 178 | NEWZEALAND |
| 179 | NICARAGUA |
| 180 | NIGER |
| 181 | NIGERIA |
| 182 | NIUE |
| 183 | NORFOLK ISLAND |
| 184 | NORTHERN MARIANA ISLANDS |
| 185 | NORWAY |
| 186 | OMAN |
| 187 | PAKISTAN |
| 188 | PALAU |
| 189 | PALMYRA ATOLL |
| 190 | PANAMA |
| 191 | PAPUA NEW GUINEA |
| 192 | PARACEL ISLANDS |
| 193 | PARAGUAY |
| 194 | PERU |
| 195 | PHILIPPINES |
| 196 | PITCAIRN ISLANDS |
| 197 | PITCAIRN, HENDERSON, DUCIE, AND OENO ISLANDS |
| 198 | POLAND |
| 199 | PORTUGAL |
| 200 | PUERTO RICO |
| 201 | QATAR |
| 202 | REUNION |
| 203 | ROMANIA |
| 204 | RUSSIA |
| 205 | RWANDA |
| 206 | SAINT BARTHELEMY |
| 207 | SAINT HELENA |
| 208 | SAINT KITTS AND NEVIS |
| 209 | SAINT LUCIA |
| 210 | SAINT MARTIN |
| 211 | SAINT PIERRE AND MIQUELON |
| 212 | SAINT VINCENT AND THE GRENADINES |
| 213 | SAMOA |
| 214 | SANMARINO |
| 215 | SAO TOME AND PRINCIPE |
| 216 | SAUDI ARABIA |
| 217 | SENEGAL |
| 218 | SERBIA |
| 219 | SEYCHELLES |
| 220 | SIERRA LEONE |
| 221 | SINGAPORE |
| 222 | SLOVAKIA |
| 223 | SLOVENIA |
| 224 | SOLOMON ISLANDS |
| 225 | SOMALIA |
| 226 | SOUTH AFRICA |
| 227 | SOUTH GEORGIA AND SOUTH SANDWICH ISLANDS |
| 228 | SPRATLY ISLANDS |
| 229 | SPAIN |
| 230 | SRI LANKA |
| 231 | ST. VINCENT & GRENADINES |
| 232 | SUDAN |
| 233 | SURINAME |
| 234 | SVALBARD |
| 235 | SWAZILAND |
| 236 | SWEDEN |
| 237 | SWITZERLAND |
| 238 | SYRIA |
| 239 | TAIWAN |
| 240 | TAJIKISTAN |
| 241 | TANZANIA |
| 242 | TERRITORIAL COLLECTIVITY OF ST. PIERRE & MIQUELON |
| 243 | TERRITORY OF AMERICAN SAMOA |
| 244 | TERRITORY OF ASHMORE AND CARTIER ISLANDS |
| 245 | TERRITORY OF CHRISTMAS ISLAND |
| 246 | TERRITORY OF COCOS (KEELING) ISLANDS |
| 247 | TERRITORY OF GUAM |
| 248 | TERRITORY OF HEARD ISLAND & MCDONALD ISLANDS |
| 249 | TERRITORY OF NORFOLK ISLAND |
| 250 | THAILAND |
| 251 | THE BAHAMAS |
| 252 | THE GAMBIA |
| 253 | TOGO |
| 254 | TOKELAU |
| 255 | TONGA |
| 256 | TRINIDAD AND TOBAGO |
| 257 | TUNISIA |
| 258 | TURKEY |
| 259 | TURKMENISTAN |
| 260 | TURKS AND CAICOS ISLANDS |
| 261 | TUVALU |
| 262 | UGANDA |
| 263 | UKRAINE |
| 264 | UNITED ARAB EMIRATES |
| 265 | UNITED KINGDOM |
| 266 | UNITED STATES VIRGIN ISLANDS |
| 267 | UNITED STATES OF AMERICA |
| 268 | URUGUAY |
| 269 | UZBEKISTAN |
| 270 | VANUATU |
| 271 | VATICAN CITY (HOLYSEE) |
| 272 | VENEZUELA |
| 273 | VIETNAM |
| 274 | VIRGIN ISLANDS, BRITISH |
| 275 | VIRGIN ISLANDS, U.S. |
| 276 | WAKE ISLAND |
| 277 | WALLIS AND FUTUNA |
| 278 | WESTERN SAHARA |
| 279 | YEMEN |
| 280 | ZAMBIA |
| 281 | ZIMBABWE |
| 282 | COMBODIA |
| 283 | CONGO |
| 284 | IVORY COAST |
| 285 | WEST INDIES |
| 286 | BRITISH VIRGIN ISLANDS |

## What the utility checks that this toolkit cannot

The utility carries Form 144's annexures and a compiled list of the natures that forbid fields 37 to 41, and it applies both at upload. The toolkit checks the shared shape (line numbering, field counts, whole-rupee challan amounts, the deposit arithmetic) and Form 144's section codes, which it has an asset for. The reason flags, the natures of remittance and the country codes have no Form 144 asset yet and are left to the utility. The message text is quoted from `assets/fvu_codes.json`, which was extracted from the utility itself.

| Code | Message |
|---|---|
| T-FV-2065 | For File Type NS1, Form Number should be 140 or 144. |
| T-FV-2130 | In Forms 140, 144 & 143, type of correction allowed are C1 (Deductor Details), C2 (Challan details), C3 (Deductee/ Party Detail), C5 (PAN Updation) and C9 (Addition of Challan and Deductee Details). |
| T-FV-4125 | Deductee detail Record number must be greater than the Deductee detail Record number of previous Deductee record. |
| T-FV-4093 | For Form no 140, 144 and 143 Rate at which Tax Deducted/Collected is mandatory. |
| T-FV-6447 | Invalid Remark for selected section code of Form 144. |
| T-FV-6452 | Invalid Section Code for Form 144. |
| T-FV-6454 | Mandatory to mention 'Certificate Number' if Remark is selected as 'A'. |
| T-FV-6455 | Invalid value under 'Certificate number of certificate issued' field. |
| T-FV-6544 | Nature of remittance is mandatory for selected Section Code. |
| T-FV-6423 | Invalid value for Nature of remittance. |
| T-FV-6425 | 'Country to which remittance is made' is mandatory for Form 144. |
| T-FV-6426 | Invalid value for 'Country to which remittance is made'. |
| T-FV-6429 | Grossing up Indicator is mandatory for Form 144. |
| T-FV-6428 | Invalid value in the field Grossing up Indicator. |
| T-FV-6476 | No value should be specified for 'Whether deductee opting out of taxation regime u/s 202(1)' for Correction other than C3. |
| T-FV-4313 | Invalid value under field 'Unique acknowledgement number' of the corresponding form 15CA. |
| T-FV-4335 | Invalid value. Please provide valid value under field 'Email ID of deductee'. |
| T-FV-4336 | Invalid value. Please provide valid value under field 'Contact number of deductee'. |
| T-FV-4337 | Invalid value. Please provide valid value under field 'Address of deductee in country of residence'. |
| T-FV-4338 | Invalid value. Please provide valid value under field 'Tax Identification Number / Unique identification number of deductee'. |
| T-FV-4340 | Value must not be provided under field 'Email ID of deductee' for the mentioned nature of remittance. |
| T-FV-4341 | Value must not be provided under field 'Contact Number of deductee' for the mentioned nature of remittance. |
| T-FV-4342 | Value must not be provided under field 'Address of deductee in country of residence' for the mentioned nature of remittance. |
| T-FV-4343 | Value must not be provided under field 'Tax Identification Number / Unique identification number of deductee' for the mentioned nature of remittance. |
| T-FV-6316 | Minor Head Code 100 is Only available for FORM 140 and FORM 144. |
| T-FV-6346 | Minor Head Code 100 only valid from FY 202324 onwards for Form 144. |

## The department's sample statement

`144RQ1_sample.txt` is the department's own sample for this form: four lines, one challan and one deductee, with 18, 72, 30 and 45 fields, CRLF line endings, and no byte outside ASCII. It confirms the file type NS1, the form number 144, the field order, and that the country code is written the way Annexure 10 stores it ('04' for Algeria, leading zero and all). It is not a model for a complete row: it leaves field 18 empty although the workbook marks it mandatory, uses reason flag A without the certificate number that flag requires, and pairs section 1042 with nature 16 although Annexure 9 allows nature 16 only for section 1046. Its deductee line, as far as it goes:

```text
fields with a value on the sample's DD line:
   4  Deductee serial number        1
   6  Mode                         O
   8  PAN                          BRNPA7678G
   9  Name                         ABCD
  12  Status                       2  (individual)
  14  Opting out                   Y
  15  Section code                 1042
  16  Nature of remittance         16 (dividend income)
  17  Country                      04 (Algeria)
  19  Date paid                    01052026
  20  Amount paid                  2100.00
  21  Grossed up                   N
  24  Tax deducted                 2000.00
  25  Tax deposited                2000.00
  27  Date of deduction            01052026
  28  Rate                         6.0000
  30  Rate basis                   B
  32  Reason flag                  A
  37  Address in country of res.   ADDRESS
  38  Email                        EAMAIL@TEST.COM
  39  Contact number               69877877878

  18  Whether deposited             left blank, though the worksheet says mandatory
```

The toolkit writes field 18, and its own fixture follows Annexure 9 where this sample does not.

## Unresolved

* What section 202(1) of the Income-tax Act, 2025 covers. The workbook gives the field a name and allows Y or N, and no material available here says more, so the module passes the value through and reads no meaning into it.
* The natures of remittance for which fields 37 to 41 must not be provided. T-FV-4340 to T-FV-4343 exist for those cases, but the list is compiled into the utility's classes and was not read out of them; there is no Java runtime here to open them. The workbook's remark names the six natures where the fields are required and no other list.
* Whether a country code below 10 is written '04' or '4'. Annexure 10 stores the codes with two characters and the sample writes '04', while DD field 17 is declared INTEGER size 3. The module writes what the document gives.
* Two deductees sharing a placeholder PAN share one `meta.non_resident` block, as described above.
* `tds lint` checks Form 144's section codes from `assets/annexures_144.json`, extracted from this workbook, but not its reason flags, natures of remittance or country codes. The flags it does know are Form 140's Annexure 6, so Form 144's own G, H and I flags would be reported as unknown. Rebuilding those three tables is outside this module.

