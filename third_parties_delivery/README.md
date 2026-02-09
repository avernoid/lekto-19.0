# **Third parties delivery**

<img src="static/description/banner.png" width="100%" alt="Banner">

**Author**: [Ganemo](https://www.ganemo.co)

## Description

This module extends the functionality of Odoo's Delivery Notes (Guías de Remisión) to allow specifying a different "Point of Arrival" address, distinct from the invoice partner. This is critical for logistics operations where the billing entity and the physical delivery location are different, such as in "Sales with delivery to third parties" (SUNAT code 03) or triangular operations.

It ensures that the generated Electronic Delivery Guide (GRE) sends the correct XML tags for the delivery address to SUNAT, maintaining compliance with Peruvian localization standards.

## Configuration

1.  Install the module.
2.  Ensure `l10n_pe_edi_stock` is installed (it effectively depends on it).
3.  No further configuration is required.

## Usage

1.  Go to **Inventory > Operations > Transfers**.
2.  Create or open a Delivery Note (Guía de Remisión).
3.  Check the box **"Deliver to third parties"** (Entregar a proveedor/comprador a terceros).
4.  A new field **"New delivery address"** (Nueva dirección de entrega) will appear.
5.  Select the contact representing the physical delivery location.
6.  Validate the transfer. The XML will now reflect this address as the arrival point.

## Credits

**Developed by**: [Ganemo](https://www.ganemo.co)