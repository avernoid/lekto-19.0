# Stock Batch Spreadsheet Report

**Unleash the power of Odoo Spreadsheet directly within Batch Pickings.**

This module integrates Odoo's native Spreadsheet engine with `stock.picking.batch`, allowing you to design, generate, and manage professional warehouse reports (Packing Lists, Delivery Slips, Analytics) without leaving Odoo or exporting to Excel.

## 🚀 Key Features

*   **Lazy Creation Workflow**: No more clutter. The "Reports" smart button only generates a file when you click it. If a report exists, it opens it instantly.
*   **Template Engine**: Design "Master" templates once using the full power of Odoo Spreadsheet (formulas, formatting, charts). The system auto-fills them with Batch data.
*   **Intelligent Archiving**: Need a fresh report? Simply select **File > Move to Trash** inside the spreadsheet. The system archives the old one, and the Smart Button resets to "0 Reports", ready to generate a new version.
*   **Granular Data Management**: A dedicated **Spreadsheets Data** menu gives you full visibility of all records, with filers for "Active Reports" vs "Orphan Templates" vs "Archived/Trash".
*   **Multi-Language Support**: Fully localized for English and **Spanish** (ES/PE), respecting standard terms like "Lote" and "Hoja de Cálculo".

---

## 📖 User Manual

### 1. Designing Templates (One-time Setup)
1.  Navigate to **Inventory > Configuration > Batch Spreadsheets > Templates**.
2.  Click **New** and give your template a name (e.g., "Master Packing List").
3.  An empty spreadsheet will open.
4.  **Crucial Step**: Use the **Data** menu (top bar) to connect to **Odoo Data**.
    *   Select `Batch Transfer` as your model.
    *   Drag and drop fields (e.g., `name`, `scheduled_date`) or lists (`move_line_ids`) into cells.
5.  Save. This is now your master layout.

### 2. Daily Operations (Warehouse Team)
1.  Open any **Batch Transfer**.
2.  Locate the **Reports** smart button (Top Right).
    *   It will show "0 Reports" initially.
3.  **Click it**: The module copies your default Template, populates it with the current Batch's real-time data, and opens it.
4.  **Use it**: Print as PDF, download as Excel, or share internally.

### 3. Resetting & Cleanup
*   **Reset**: To delete a report and start over, open the spreadsheet and click **File > Move to Trash**. The smart button on the Batch will reset.
*   **Empty Trash**: To permanently delete files, go to **Inventory > Configuration > Batch Spreadsheets > Spreadsheets Data**. Use the **"Archived"** filter to find and delete old records.

---

## 🛠 Technical Details

*   **Dependencies**: `spreadsheet_edition`, `stock_picking_batch`.
*   **Models**:
    *   `stock.batch.spreadsheet`: The actual report instances.
    *   `stock.batch.spreadsheet.template`: The master designs.
    *   `stock.picking.batch`: Extended with smart button logic.
*   **Security**: Uses standard Odoo security groups (Inventory User/Manager).

---

## 💙 Credits & Support

**Developed by Ganemo**  
*The #1 Odoo Partner for High-Quality Apps & Localization in LatAm.*

*   **Website**: [https://www.ganemo.co](https://www.ganemo.co)
*   **Contact**: [leads@ganemo.co](mailto:leads@ganemo.co)
*   **WhatsApp**: [+1 (828) 672-6150](https://api.whatsapp.com/send?phone=18286726150)
