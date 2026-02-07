# **RUC Validation SUNAT**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Validate Peruvian RUC (Tax ID) instantly. Auto-fill company data and ensure fiscal compliance.**

## **Summary**
This module integrates your Odoo instance directly with the SUNAT (Peruvian Tax Authority) query service. It eliminates manual data entry errors by automatically fetching legal company details when you enter a RUC number. It retrieves the official Legal Name, Fiscal Address (Street, District, Province, Department), Taxpayer Status (Active/Suspended), and Taxpayer Condition (Habido/No Habido).

---

## **Table of Contents**
1. [Features](#features)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [FAQ & Troubleshooting](#faq)
6. [Credits](#credits)

---

## **Features**
*   **Real-time Validation**: Connects directly to SUNAT to verify if a RUC exists.
*   **Auto-Fill Data**: Automatically populates:
    *   **Legal Name**: The official name registered with SUNAT.
    *   **Address**: Full address including District, Province, and Department (Ubigeo).
    *   **Commercial Name**: If available.
*   **Status Check**: Verifies if the taxpayer is **Active** and **Habido** (Domiciled), critical for tax compliance.
*   **Odoo Native Integration**: Works seamlessly within the standard Contacts form (`res.partner`).

---

## **Installation**
1.  Go to **Apps**.
2.  Search for **RUC Validation SUNAT** (`ruc_validation_sunat`).
3.  Click **Install**.

*Note: This module automatically installs `l10n_pe_catalog`, `document_type_validation`, and `first_and_last_name` as dependencies.*

---

## **Configuration**
This module requires a valid API Token from Ganemo.
1.  **Install**: Install the module `ruc_validation_sunat`.
2.  **Peruvian Catalogues**: Ensure `l10n_pe_catalog` is installed.
3.  **Company Settings**:
    *   Go to **Settings > Companies > [Your Company]**.
    *   Open the **General Information** tab.
    *   Enter your **RUC Query Token** (contact Ganemo Sales if you don't have one).
    *   Ensure Country is set to **Peru**.
4.  **Internet Access**: The Odoo server must have internet access to reach the validation service.

---

## **Usage**

### **1. Validating a New Customer/Vendor**
1.  Go to **Contacts** (or Sales/Accounting > Customers/Vendors).
2.  Click **New**.
3.  Select **Company** (or Individual if they have a RUC 10...).
4.  In the "Tax ID Type" field (Document Type), select **RUC**.
5.  Enter the **11-digit RUC number** in the **Tax ID** (VAT) field.
6.  The system will automatically query SUNAT.
    *   *If valid:* The Name, Address, and other fields will populate instantly.
    *   *If invalid:* You will receive a notification that the RUC does not exist.

### **2. Updating an Existing Contact**
1.  Open the contact card.
2.  Ensure the Tax ID is correct.
3.  (Optional) If you have a "SUNAT Query" button, click it to refresh data from SUNAT.

---

## **FAQ**

**Q: The data isn't loading when I enter the RUC.**
*   **A:** Check if the SUNAT service is operational or if your Token is valid/active. Also check your server's Internet connection.

**Q: invalid RUC error?**
*   **A:** Ensure you entered exactly 11 digits and the Checksum is correct. SUNAT rejects invalid numbers.

**Q: How do I get the RUC Query Token?**
*   **A:** You need a valid subscription. Contact the Ganemo Sales team (<leads@ganemo.com>).

**Q: Can I use this for DNI (National ID) validation?**
*   **A:** No, this module allows connection for RUC queries. For DNI validation, you need `l10n_pe_reniec` or similar.

**Q: Does it support multi-company?**
*   **A:** Yes. Validation logic is applied per-record and respects your company environment.

**Q: Can I validate RUCs for foreign countries?**
*   **A:** No, this service is exclusive to Peru (`l10n_pe`).

---

## **Credits**

**Author**: [Ganemo](https://www.ganemo.com)

**Maintainer**: Ganemo (<mailto:soporte@ganemo.com>)

**Website**: [https://www.ganemo.com](https://www.ganemo.com)

---

*Need support? Contact us at [leads@ganemo.com](mailto:leads@ganemo.com)*
