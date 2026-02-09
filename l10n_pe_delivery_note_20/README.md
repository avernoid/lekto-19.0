# Peruvian - Electronic Delivery Note Extension

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.com)

## Overview

This module extends the native Odoo functionality for Peruvian Electronic Delivery Notes (`l10n_pe_edi_stock`) to provide full compliance with SUNAT requirements, specifically for complex logistics operations involving multiple branches, returns, and third-party deliveries.

While the base Odoo module assumes all transfers originate from the company's fiscal address (Annex Code '0000'), **this extension intelligently resolves the correct "Annexed Establishment" code** for every address involved in the transfer chain.

## Key Features

*   **Multi-Branch Support**: Correctly identifies the *Annexed Establishment* code (e.g., 0001, 0002) for source and destination warehouses, ensuring SUNAT accepts transfers between specific company locations.
*   **Extended Transfer Reasons**: Adds support for the full SUNAT Catalog 20, including:
    *   `02`: Purchase
    *   `06`: Return (Devolución)
    *   `07`: Pick up of transformed goods
    *   `08`: Import
    *   `09`: Export
    *   `13`: Others
*   **Third-Party Delivery Logic**: distinct handling for transfers involving customers, suppliers, or logistics operators.
*   **Enhanced Vehicle Support**: Specific handling for M1L vehicles and distinguishing between Public vs. Private transport modes.

## Configuration

### 1. Configure Branch Addresses
To ensure the XML is generated with the correct address codes:
1.  Go to **Contacts**.
2.  Open the contact record associated with your Warehouse or Branch.
3.  Ensure the **Address Type** is correctly set (e.g., Delivery Address, Other).
4.  Set the **Annexed Establishment** code (e.g., `0001`) in the Peruvian Localization tab/section.
    *   *Note: Takes precedence over the company's default '0000'.*

### 2. Configure Picking Types (Optional)
For specific operation types, you can define default transport modes (Public/Private) to speed up data entry.

## Technical Detail: XML Address Handling

SUNAT requires the specific 4-digit code of the establishment (e.g., "0000" for HQ, "0001" for Branch 1) in the XML UBL tag `<cbc:AddressTypeCode>`.

**Logic Flow:**
The system evaluates 3 main scenarios to populate this tag. **Crucial:** The code is filled ONLY if the address owner's RUC starts with **'6'** (Legal Entities/Companies).

### 1. Source Address (`cac:DespatchAddress`)
*Where does the merchandise come from?*

| Scenario | Condition (Odoo) | Source of Annex Code |
| :--- | :--- | :--- |
| **Return** | `l10n_pe_edi_reason_for_transfer == '06'` | Partner of the document (`record.partner_id`) |
| **Third Party Delivery** | `deliver_to_third_parties` is True | **In:** Customer (`record.customer_id`)<br>**Out:** Origin Location (`record.location_id.direction_id`) |
| **Standard** | (None of the above) | **Out/Int:** Origin Location (`record.location_id.direction_id`)<br>**In:** Partner (Vendor) (`record.partner_id`) |

### 2. Destination Address (`cac:DeliveryAddress`)
*Where does the merchandise arrive?*

| Scenario | Condition (Odoo) | Source of Annex Code |
| :--- | :--- | :--- |
| **Return** | `l10n_pe_edi_reason_for_transfer == '06'` | Partner of the document (`record.partner_id`) |
| **Third Party Delivery** | `deliver_to_third_parties` is True | **In:** Destination Location (`record.location_dest_id.direction_id`)<br>**Out:** Customer (`record.customer_id`) |
| **Standard** | (None of the above) | **In/Int:** Destination Location (`record.location_dest_id.direction_id`)<br>**Out:** Partner (Customer) (`record.partner_id`) |

> **Practical Example: Standard Sale (Out)**
> *   **Case:** You sell goods to a customer from your Main Warehouse.
> *   **Departure:** Takes code from YOUR warehouse (`location_id.direction_id`), because it's a standard outgoing shipment.
> *   **Arrival:** Takes code from the CUSTOMER (`partner_id`), because it's a standard outgoing shipment.
>
> *Crucial: Both your warehouses (address type partners) and your customers must have this field available.*

## Usage

### Creating a Compliant Delivery Note

1.  Create a standard **Transfer (Picking)** in Inventory.
2.  Select the **Reason for Transfer** (Motivo de Traslado).
    *   *Example: For returning goods to a supplier, select "Devolución" (06).*
3.  Select the **Transport Type**:
    *   **Public**: If using an external carrier. Requires a valid Operator/Carrier with RUC and Permit Number.
    *   **Private**: If using your own vehicles. Requires a Vehicle and Driver configuration.
4.  **Validate** the transfer.
5.  The system will generate the Electronic Delivery Note (GRE) XML.
    *   It automatically checks the `annexed_establishment` of the Source and Destination contacts.
    *   If the Reason is "Import/Export", it adjusts the address logic accordingly.

## Troubleshooting

*   **Error: "Address Code Missing"**: Ensure the Source and Destination contacts have a valid `annexed_establishment` code set. If it's the main office, set it to `0000` (or leave empty if the system defaults to 0).
*   **XML Rejected by SUNAT**: Verify that the *Reason for Transfer* matches the operation type (e.g., don't use "Sale" for a transfer between internal warehouses).

---

**Developed with ❤️ by [Ganemo](https://www.ganemo.com)**
