# Form 140 (resident non-salary) record layout

Generated from the department's own file-format workbook, `Form140_FileFormat_v1.2_22072026.xlsx`, sheet `File Format_R`. Do not hand-edit; rerun `scripts/extract_annexures.py`.

The statements in this pipeline write these records exactly as described here. Where a remark imposes a rule, the rule is quoted in full.

| Record | Fields | Meaning |
|---|---:|---|
| FH | 18 | File header, once per file |
| BH | 72 | Batch header, once per batch |
| CD | 30 | Challan detail, once per challan |
| DD | 45 | Deductee detail, once per deductee |

A regular statement carries exactly one batch, so a file is: one FH, one BH, then for each challan a CD immediately followed by its DD records.

## FH record

| # | Field | Form col. | Type | Size | M/O | Remark |
|---:|---|---|---|---:|---|---|
| 1 | Line Number | NA | INTEGER | 9 | M | Running Sequence Number for each line in the file. |
| 2 | Record Type | NA | CHAR | 2 | M | Value should be "FH" signifying 'File Header' record |
| 3 | File Type | NA | CHAR | 4 | M | Value should be "NS1" for FN 140 |
| 4 | Upload Type | NA | CHAR | 2 | M | Value should be R |
| 5 | File Creation Date | NA | DATE | 8 | M | Mention the date of creation of the file in ddmmyyyy format. |
| 6 | File Sequence No. | NA | INTEGER | 9 | M | Indicates the running sequence number for the file. (Should be unique across all the files) |
| 7 | Uploader Type | NA | CHAR | 1 | M | Value should be D |
| 8 | TAN of Deductor | NA | CHAR | 10 | M | TAN of Deductor |
| 9 | Total No. of Batches | NA | INTEGER | 9 | M | Indicates the number of batches that the file contains. |
| 10 | Name of Return Preparation Utility | NA | CHAR | 75 | M | Name of the software used for preparing the Quarterly e-TDS/TCS statement should be mentioned. |
| 11 | Record Hash (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 12 | FVU Version (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 13 | File Hash (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 14 | Sam Version (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 15 | SAM Hash (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 16 | SCM Version (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 17 | SCM Hash (Not applicable) | NA | NA | 0 | NA | No value should be specified |
| 18 | Consolidated file hash | NA | NA | 0 | NA | No value should be specified |

## BH record

| # | Field | Form col. | Type | Size | M/O | Remark |
|---:|---|---|---|---:|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | Running Sequence Number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | Value should be "BH" (Batch Header) for the batch header record |
| 3 | Batch Number | – | INTEGER | 9 | M | Value must start with 1. |
| 4 | Count of Challan/transfer voucher Records | – | INTEGER | 9 | M | Count of total number of challans/transfer vouchers contained within the batch. |
| 5 | Form Number | – | CHAR | 4 | M | Value must be 140. |
| 6 | Transaction Type (Not applicable) | – | NA | 0 | O | No value should be specified |
| 7 | Batch Updation Indicator (Not applicable) | – | NA | 0 | O | No value should be specified |
| 8 | Original Token Number (Token Number of Regular statement) - (Not applicable) of the statement | – | NA | 0 | O | No value should be specified |
| 9 | Token no. of previous regular statement (Form no. 140). | – | INTEGER | 15 | O | If value present in field no. 52 is "Y", mandatory to mention 15 digit Token number of immediate previous regular statement for Form 140, else no value to be provided. |
| 10 | Token Number of the statement submitted - (Not applicable) | – | NA | 0 | O | No value should be specified |
| 11 | Token Number date - (Not applicable) | – | NA | 0 | O | No value should be specified |
| 12 | Last TAN of Deductor / Collector ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 13 | TAN of Deductor | – | CHAR | 10 | M | Mention the 10 Character TAN of the deductor. Should be all CAPITALS. |
| 14 | Receipt number (eight digit) provided by TIN | – | CHAR | 8 | NA | No value should be specified |
| 15 | PAN of Deductor | – | CHAR | 10 | M | Mandatory to mention the PAN of the Deductor. If deductor is not required to have a PAN mention PANNOTREQD |
| 16 | Assessment Yr | – | INTEGER | 6 | M | Assessment year e.g. value should be 202728 for Tax Year 2026-07. Value should be greater than or equal to 202728. |
| 17 | Tax Year | NA | INTEGER | 6 | M | Tax Year (YYYYYY) as per Act; e.g., 202627 for Tax Year 2026-27 |
| 18 | Period | – | CHAR | 2 | M | Valid values Q1, Q2, Q3, Q4 of the financial Year. Q1 for 1st Quarter, Q2 for 2nd Quarter, Q3 for 3rd Quarter and Q4 for 4th Quarter. |
| 19 | Name of Deductor | – | CHAR | 75 | M | Mention the Name of the Employer / Deductor I.e. Employer / Deductor who deducts tax. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 20 | Deductor Address 6 (Country/Region) | NA | CHAR | 25 | M | Mention the address line 6 of the Employer. Only special characters are not allowed under this field. |
| 21 | Deductor Address1 (Flat/Door/Block number) | – | CHAR | 25 | M | Mention the address line 1 of the Employer. Only special characters are not allowed under this field. |
| 22 | Deductor Address2 (Post Office) | – | CHAR | 25 | O | Mention the address line 2 of the Employer. Only special characters are not allowed under this field. |
| 23 | Deductor Address3 (Road/Street/Block/Sector) | – | CHAR | 25 | O | Mention the address line 3 of the Employer. Only special characters are not allowed under this field. |
| 24 | Deductor Address4 (Area/locality) | – | CHAR | 25 | O | Mention the address line 4 of the Employer. Only special characters are not allowed under this field. |
| 25 | Deductor Address5 (District) | – | CHAR | 25 | O | Mention the address line 5 of the Employer. Only special characters are not allowed under this field. |
| 26 | Deductor's Address - State | – | INTEGER | 2 | M | Numeric code for state. For list of State codes, refer to the Annexure 1 below. |
| 27 | Deductor's Address - Pincode | – | INTEGER | 6 | M | PIN Code of Deductor . |
| 28 | Deductor's Email ID | – | CHAR | 75 | M | Valid E-mail should be provided. 1. Email format must be checked -atleast @ and '.' should be mentioned.  2. Both @ and '.' should be preceded and succeeded by atleast one character. 3. At least one '.' should come after '@'. 4. All printable characters allowed except '^' and space. 5. This field is mandatory if no value is provided under field no. 42 i.e. "Responsible Person's Email ID -1" of Batch Header.  E-mail id of deductor/collector or person responsible for deducting/collecting tax should be provided. |
| 29 | Deductor Contact Country Code | – | INTEGER | 5 | M | Country calling code for deductor contact number (e.g., 91 for India). |
| 30 | Deductor Contact Number | – | CHAR | 10 | M | Deductor contact number without country code; digits only. Max 15. |
| 31 | Filler 1 | – | CHAR | 0 | O | No value to be specified. |
| 32 | Deductor Type | – | CHAR | 1 | M | Deductor category code to be mentioned as per Annexure 4 |
| 33 | Name of Person responsible for Deduction | – | CHAR | 75 | M | Mention the Name of Person responsible for paying salary on behalf of the deductor. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 34 | Designation of the Person responsible for Deduction | – | CHAR | 20 | M | Mention the designation of Person responsible for paying salary on behalf of the deductor. Only blank values or only special characters or only dots, spaces etc. (i.e. `~!@#$%^&*( )_+,./?;:’”[{]}\\|) are not allowed under this field. |
| 35 | Responsible Person's Address1 (Flat/Door/Block number) | – | CHAR | 25 | M | Mention the address line 1 of the responsible Person. Only special characters are not allowed under this field. |
| 36 | Responsible Person's Address2 (Post Office) | – | CHAR | 25 | O | Mention the address line 2 of the responsible Person. Only special characters are not allowed under this field. |
| 37 | Responsible Person's Address3 (Road/Street/Block/Sector) | – | CHAR | 25 | O | Mention the address line 3 of the responsible Person. Only special characters are not allowed under this field. |
| 38 | Responsible Person's Address4 (Area/locality) | – | CHAR | 25 | O | Mention the address line 4 of the responsible Person. Only special characters are not allowed under this field. |
| 39 | Responsible Person's Address5 (District) | – | CHAR | 25 | O | Mention the address line 5 of the responsible Person. Only special characters are not allowed under this field. |
| 40 | Responsible Person's State | – | INTEGER | 2 | M | Numeric code for state. For list of State codes, refer to the Annexure 1 below. |
| 41 | Responsible Person's PIN | – | INTEGER | 6 | M | PIN Code of Responsible Person . |
| 42 | Responsible Person's Email ID -1 | – | CHAR | 75 | M | Valid E-mail should be provided. 1. Email format must be checked -atleast @ and '.' should be mentioned.  2. Both @ and '.' should be preceded and succeeded by atleast one character. 3. At least one '.' should come after '@'. 4. All printable characters allowed except '^' and space. 5. This field is mandatory if no value is provided under field no. 28 i.e. "Deductor's Email ID" of Batch Header.  E-mail id of deductor/collector or person responsible for deducting/collecting tax should be provided. |
| 43 | Responsible Persons country region | NA | CHAR | 25 | M | Mention the country of the responsible person . Only special characters are not allowed under this field. |
| 44 | Responsible Person Contact Country/Region | NA | INTEGER | 5 | M | Country calling code for person responsible contact number (e.g., 91). |
| 45 | Responsible Person Contact Number | NA | CHAR | 10 | M | Contact number (digits) for person responsible; max 10. |
| 46 | Filler 3 | NA | NA | 0 | O | No value should be specified |
| 47 | Batch Total of - Total of Deposit Amount as per Challan | – | INTEGER | 15 | M | Mention the Total of Deposit Amount as per Challan.The value here should be same as sum of values in field 'Total of Deposit Amount as per Challan' in the 'Challan Detail' record ( please refer to the Challan Detail' record section below ). Paisa Field (Decimal Value) of the Amount must be 00. |
| 48 | Unmatched challan count | – | CHAR | 9 | O | No value to be specified. |
| 49 | Count of Salary Details Records (Not applicable) | – | NA | 0 | O | No value should be specified |
| 50 | Batch Total of - Gross Total Income as per Salary Detail (Not applicable) | – | NA | 0 | O | No value should be specified |
| 51 | Filler 4 | NA | NA | 0 | O | No value should be specified |
| 52 | Whether regular statement for Form 140 filed for earlier period | – | CHAR | 1 | M | "Y" if regular statement for Form 140 has been filed for earlier period, else value "N" should be provided. |
| 53 | Last Deductor Type | – | CHAR | 1 | NA | No value should be specified |
| 54 | State Name | – | CHAR | 2 | O | Numeric code for state should be mentioned as per Annexure 5. Mandatory if deductor type is State Govt. (code S), Statutory body - State Govt. (code E), Autonomous body - State Govt. code H) and Local Authority - State Govt. (code N). For other deductor category no value should be provided. |
| 55 | Filler 5 | NA | NA | 0 | O | No value should be specified |
| 56 | Filler 6 | NA | NA | 0 | O | No value should be specified |
| 57 | Ministry Name | NA | CHAR | 3 | O | Numeric code for Ministry name should be provided. For list of Ministry name codes, refer to the Annexure 3 below. Mandatory for following deductor types: Central Govt (A), Statutory body - Central Govt. (D) & Autonomous body - Central Govt. (G). Optional for deductor type Statutory body - State Govt. (E), Autonomous body - State Govt. (H), Local Authority - Central Govt. (L) & Local Authority -State Govt. (N).   For other deductor type no value should be provided. |
| 58 | Ministry Name (Others) | NA | CHAR | 150 | O | If numeric code '99' (i.e. Other) is provided in Ministry Name field then value in Ministry Name "Other" field should be provided |
| 59 | PAN of Responsible Person | – | CHAR | 10 | M | Quote ten digit valid PAN of the person responsible (as quoted in field no. 33 above) for deducting tax. |
| 60 | Filler 7 | NA | NA | 0 | O | No value should be specified |
| 61 | Filler 8 | NA | NA | 0 | O | No value should be specified |
| 62 | Filler 9 | NA | NA | 0 | O | No value should be specified |
| 63 | Filler 10 | NA | NA | 0 | O | No value should be specified |
| 64 | Filler 11 | NA | NA | 0 | O | No value should be specified |
| 65 | Filler 12 | NA | NA | 0 | O | No value should be specified |
| 66 | Filler 13 | NA | NA | 0 | O | No value should be specified |
| 67 | Filler 14 | NA | NA | 0 | O | No value should be specified |
| 68 | Account Office Identification Number (AIN) of PAO/ TO/ CDDO | – | CHAR | 7 | O | Mandatory to mention value only in case the deductor category is "Central Govt." or "State Govt." and mode of deposit of TDS/TCS is through 'Book Entry' i.e., value in the field no. 37 of challan/ transfer voucher details is "Y". Mention AIN of the below: 1) Pay and Account Office (PAO) 2) Treasure Office (TO) 3) Cheque Drawing and Disbursing Officer (CDDO) |
| 69 | Goods and Service Tax Number (GSTN) | – | CHAR | 15 | O | Mention 15 digit valid Goods and Service Tax Number (GSTIN). |
| 70 | Count of Section 194P Detail Records (Not applicable) | – | NA | 0 | O | No value should be specified |
| 71 | Batch Total of - Gross Total Income as per Section 194P Detail (Not applicable) | – | NA | 0 | O | No value should be specified |
| 72 | Record Hash (Not applicable) | – | NA | 0 | O | No value should be specified |

## CD record

| # | Field | Form col. | Type | Size | M/O | Remark |
|---:|---|---|---|---:|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | Running sequence number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | Value "CD" (Challan Detail) for Challan Detail record |
| 3 | Batch Number | – | INTEGER | 9 | M | Value should be same as 'Batch Number' field in 'Batch Header' record. |
| 4 | Challan-Detail Record Number | A | INTEGER | 9 | M | Running serial number for 'Challan Detail' records in a batch. Should start with 1 |
| 5 | Count of Deductee / Party Records | – | INTEGER | 9 | M | Count of total number of 'Deductee Detail Records' within e-TDS statement. Value Should be >= 0 |
| 6 | NIL Challan Indicator | – | CHAR | 1 | M | Value should be "N". In cases where no tax has been deposited in bank, value should be "Y" (applicable in case of NIL return) |
| 7 | Challan Updation Indicator (Not applicable) | – | NA | 0 | O | No value should be specified |
| 8 | Total tax Deducted | B | INTEGER | 15 | M | Mention the amount of "Income Tax" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 9 | Total Interest | C | INTEGER | 15 | M | Mention the amount of "Interest" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 10 | Total fee | D | INTEGER | 15 | M | Mention the amount of "Fee" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 11 | Total Penalty/ Others | E | INTEGER | 15 | M | Mention the amount of "Penalty" out of the 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value. |
| 12 | Total of Deposit Amount as per Challan/Total Amount adjusted through Book Adjustment (Total of values in B+C+D+E) | F | INTEGER | 15 | M | Mention the amount of 'Total tax deposited' through Challan. No fractional portion is allowed in this field (value should be integer) , I.e. value "1000.50" will not be allowed, whereas value "1000.00" will be considered to be valid value.  Value in this field should be equal to total of values in column numbers B, C, D, E.  In case of challan (i.e. value under field 13 is C), value in this field should be greater than or equal to: Total tax deposited amount (field no. 25 of all deductee details mapped to corresponding challan) + Interest allocation (field no. 24 of challan details) + Other allocation (field no. 25 of challan details) + Fee amount (field no. 10 of challan details)  In case of transfer voucher (i.e. value under field 13 is B), value in this field should be greater than or equal to: Total tax deposited amount (field no. 25 of all deductee details mapped to corresponding challan) + Interest allocation (field no. 24 of challan details) + Other allocation (field no. 25 of challan details) |
| 13 | Mode of payment of tax (by way of challan/by way of book adjustment) | G | CHAR | 1 | O | Allowed values C or B If Transfer Voucher Number is provided this is mandatory and only allowed value is 'B'. If Bank Challan Number is provided , then mention value as "C". For a Nil statement no value to be provided. Value 'C' to be provided, if values under field no. 15 of DD details are '1059', '1034', '1038' or '1061'. |
| 14 | Last BSR Code/ Form 24G Receipt Number ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 15 | BSR Code/ Form 24G Receipt Number | H | INTEGER | 7 | M | In case TDS deposited by  1) Challan:BSR Code of the receiving branch 2) Book Adjustment: Quote seven digit receipt number provided by AO. Applicable for govt. deductor/ collector where TDS is deposited by book entry.  3) No value to be quoted in case of Nil Statement (value in field "NIL Challan Indicator" field is "Y"). |
| 16 | Last Bank Challan No/DDO Serial Number ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 17 | Bank Challan No/DDO Serial Number | J | INTEGER | 5 | O | Challan Number issued by Bank if value in field G is C DDO Serial Number if value in column G is B  Applicable to both Govt and Non Govt, Non-Nil statements. No value is required to be provided in case of a NIL return (I.e. the cases in which the value in field 'NIL Challan Indicator' is "Y"). |
| 18 | Last Date of 'Bank Challan No / DDO Serial Number' ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 19 | Date of 'Bank Challan / Transfer Voucher' (DDMMYYYY) | I | DATE | 8 | M | Date of payment of tax to Govt. It can be any date on or after 1st April of immediate previous financial year for which the return is prepared. Value should be equal to last date of respective quarter if the value in field "NIL Challan Indicator" is "Y".  Date of 'Bank Challan / Book Adjustment' should be within the respective quarter for which statement is being filed, in case of minor head code value selected under field no. 23 is '100'. Also this date has to be on or before date present under field 'Date on which Amount paid / Credited' field no. 19 of DD record (which is mapped to this challan with minor head code value '100') |
| 20 | Last Total of Deposit Amount as per Challan ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 21 | Total Tax Deposited Amount as per Collectee annexure (Total Sum of column no. L) for the specified challan | – | DECIMAL | 15 | M | Mention the sum of 'Deductee Deposit Amount' of the underlying Deductee Records |
| 22 | Total Tax Deducted Amount as per Deductor annexure (Total sum of Column no. J) for the specified challan | – | DECIMAL | 15 | M | Total sum of tax collected of the deductee details for the respective Challan |
| 23 | Minor Head of Challan | K | INTEGER | 3 | O | Mention value as marked on challan - refer Annexure 7 for minor head For Minor head code 100: If DD details are having section code '1059', '1034', '1038' or '1061', then minimum 1 deductee should be there for challans having minor head code 100. |
| 24 | Interest Allocation | – | INTEGER | 15 | M | Mention interest allocation. Only integer values are allowed. The value of 1000 should be represented as 1000.00 in this field. Mention value as provided in field no. 9 of CD details. |
| 25 | Other Allocation | – | INTEGER | 15 | M | Mention fees allocation. Only integer values are allowed for this field. The value of 1000 should be represented as 1000.00 in this field. Mention value as provided in field no. 11 of CD details. |
| 26 | Filler 3 | – | NA | 0 | O | No value should be specified |
| 27 | Filler 4 | – | NA | 0 | O | No value should be specified |
| 28 | Filler 5 | – | NA | 0 | O | No value should be specified |
| 29 | Filler 6 | – | NA | 0 | O | No value should be specified |
| 30 | Record Hash (Not applicable) | – | NA | 0 | O | No value should be specified |

## DD record

| # | Field | Form col. | Type | Size | M/O | Remark |
|---:|---|---|---|---:|---|---|
| 1 | Line Number | – | INTEGER | 9 | M | Running Sequence Number for each line in the file |
| 2 | Record Type | – | CHAR | 2 | M | Value "DD"(Deductee Detail) for Deductee-detail record |
| 3 | Batch Number | – | INTEGER | 9 | M | Value should be same as 'Batch Number' field in 'Batch Header' record |
| 4 | Deductee / Party Detail Record No | A | INTEGER | 9 | M | Running serial no to indicate detail record no. |
| 5 | Challan reference Number | B | INTEGER | 9 | M | Running serial number for 'Challan Detail' records in a batch. |
| 6 | Mode | – | CHAR | 1 | M | Value should be O |
| 7 | Last deductee PAN ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 8 | Deductee's PAN | C | CHAR | 10 | M | PAN of the Employee. If available should be Valid PAN Format. There may be Employees who have not been issued PAN however who have applied for a PAN and have given adequate declaration to the deductor indicating the same. In such cases, deduction schedule in the statement will not reflect PAN and instead state PAN Ref. Number for the Employee. The deductor will however have to mention ‘PANAPPLIED’ in place of PAN. If the Employee is not sure of the PAN format he will have to mention 'PANINVALID'. However if the Employee has not given any declaration, deductor will have to mention ‘PANNOTAVBL’ in place of PAN.   For section codes '1059', '1034', '1038' or '1061', no default PAN values should be allowed under this field. That means default PAN values in case of non-availablity of valid PAN ('PANNOTAVBL', 'PANAPPLIED', 'PANINVALID') will not be allowed for these sections. |
| 9 | Name of the Deductee | D | CHAR | 75 | M | Mention the Name of the deductee. |
| 10 | Remarks 1 (for future use) | – | NA | 0 | O | No value should be specified |
| 11 | Remarks 2 (for future use) | – | NA | 0 | O | No value should be specified |
| 12 | Remarks 3 (for future use) | – | NA | 0 | O | No value should be specified |
| 13 | Remarks 4 (for future use) | – | NA | 0 | O | No value should be specified |
| 14 | Remarks 5 (for future use) | – | NA | 0 | O | No value should be specified |
| 15 | Section Code | E | CHAR | 4 | M | As per Annexure 2 |
| 16 | Remarks 6 (for future use) | – | NA | 0 | O | No value should be specified |
| 17 | Remarks 7 (for future use) | – | NA | 0 | O | No value should be specified |
| 18 | Whether the total amount of tax deducted as mentioned in Column (J) has been deposited (Yes/No) | K | CHAR | 1 | M | Value should either "Y" or "N" |
| 19 | Date of payment / Credited (dd/mm/yyyy) | F | DATE | 8 | M | Date on which Amount paid/ Credited /Debited to deductee. The value under the “Date of Payment / Date on which Amount Collected / Debited” field shall fall within the quarter and financial year to which the statement pertains· |
| 20 | Amount Paid/ Credited | G | DECIMAL | 15 | M | Mention the Amount paid to deductee. Value should always be greater than 0.00 |
| 21 | Grossing up Indicator (Not applicable) | – | NA | 0 | O | No value should be specified |
| 22 | Amount of cash withdrawal in excess of Rs. 1 crore as referred to in section 393(3) [Table: Sl. No. 5] (in case of person other than cooperative society) | H | DECIMAL | 15 | O | Mandatory to mention value under this field only when value under field Section Code (field no. 15) of DD records is "section 393(3), i.e. section code 1065", else no value should be specified. |
| 23 | Amount of cash withdrawal which is in excess of Rs. 3 Crore for cases covered by section 393(3) [Table: Sl. No. 5] (in case of co- operative societies) | I | DECIMAL | 15 | O | Mandatory to mention value under this field only when value under field Section Code (field no. 15) of DD records is "section 393(3), i.e. section code 1064", else no value should be specified. |
| 24 | Total Tax Deducted | J | DECIMAL | 15 | M | Decimal with precision value 2 is allowed.  In case value present under field 15 is 1059', '1034', '1038' or '1061', then value under this field should be 0.00. |
| 25 | Total Tax Deposited | L | DECIMAL | 15 | M | Decimal with precision value 2 is allowed.  In case value present under field 15 is 1059', '1034', '1038' or '1061', then value under this field should be 0.00. |
| 26 | Last total Tax deducted (Used for Verification) (Not Applicable) | – | NA | 0 | O | No value should be specified |
| 27 | Date of deduction (dd/mm/yyyy) | N | DATE | 8 | M | Date of tax deduction. Mandatory if 'Total tax deducted' is greater than Zero (0.00) . No value needs to be specified if 'Total Tax Deducted' is Zero (0.00) . Date to be mentioned in DDMMYYYY format. Also, this date should not be less than the relevant quarter. E.g. If the statement is being prepared for Q2 of Tax Year 2026-27, then date of deduction should be greater than or equal to 01/07/2026. |
| 28 | Rate at which Tax Deducted | M | DECIMAL | 7 | M | Rate at which Tax is deducted, with decimal precision of 4 point. E.g. if the rate is 2 then the same should be mentioned as 2.0000. If value in field 'Total tax collected' is 0.00 then rate at which tax deducted should be 0.0000 In case value present under field 15 is 1059', '1034', '1038' or '1061', then value under this field should be 0.00. |
| 29 | Remarks 9 (for future use) | – | NA | 0 | O | No value should be specified |
| 30 | Remarks 10 (for future use) | – | NA | 0 | O | No value should be specified |
| 31 | Unique Identification  Number of Form No.  121 submitted by the  deductee | Q | CHAR | 26 | O | Mention value of Unique Identification Number of Form No. 121. Value should be 26 characters. |
| 32 | Reason for non-deduction / Lower deduction / Higher deduction / Threshold / Transporter etc. | O | CHAR | 1 | O | If applicable quote value (code) as per Annexure 6_ else no value to be provided. |
| 33 | Certificate number of certificate issued under section 395 for non-deduction /lower deduction | P | CHAR | 15 | O | Mandatory to mention 10 or 15 digit alphanumeric value if, "A" is mentioned in field no. 32 (Remark field). |
| 34 | Filler 1 | – | NA | 0 | O | No value should be specified |
| 35 | Filler 2 | – | NA | 0 | O | No value should be specified |
| 36 | Filler 3 | – | NA | 0 | O | No value should be specified |
| 37 | Filler 4 | – | NA | 0 | O | No value should be specified |
| 38 | Filler 5 | – | NA | 0 | O | No value should be specified |
| 39 | Filler 6 | – | NA | 0 | O | No value should be specified |
| 40 | Filler 7 | – | NA | 0 | O | No value should be specified |
| 41 | Filler 8 | – | NA | 0 | O | No value should be specified |
| 42 | Last Total Tax Deposited ( Used for Verification) (Not applicable) | – | NA | 0 | O | No value should be specified |
| 43 | Filler 10 | – | NA | 0 | O | No value should be specified |
| 44 | Filler 11 | – | NA | 0 | O | No value should be specified |
| 45 | Record Hash (Not applicable) | – | NA | 0 | O | No value should be specified |
