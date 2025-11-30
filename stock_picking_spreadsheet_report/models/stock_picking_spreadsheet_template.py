from odoo import models, fields, _

class StockPickingSpreadsheetTemplate(models.Model):
    _name = "stock.picking.spreadsheet.template"
    _description = "Stock Picking Spreadsheet Template"

    name = fields.Char(required=True)
    spreadsheet_id = fields.Many2one("stock.picking.spreadsheet", ondelete="cascade")
    spreadsheet_binary_data = fields.Binary(related="spreadsheet_id.spreadsheet_binary_data")
    spreadsheet_file_name = fields.Char(related="spreadsheet_id.spreadsheet_file_name")

    def action_create_spreadsheet(self):
        self.ensure_one()
        vals = {"name": self.name}
        if self.spreadsheet_id:
            vals.update({
                "spreadsheet_binary_data": self.spreadsheet_id.spreadsheet_binary_data,
                "spreadsheet_file_name": self.spreadsheet_id.spreadsheet_file_name,
            })
            if self.spreadsheet_id.spreadsheet_data:
                vals["spreadsheet_data"] = self.spreadsheet_id.spreadsheet_data
            
        spreadsheet = self.env["stock.picking.spreadsheet"].create(vals)
        self.spreadsheet_id = spreadsheet.id
        return spreadsheet.action_open_spreadsheet()

    def action_open_spreadsheet(self):
        self.ensure_one()
        return self.spreadsheet_id.action_open_spreadsheet()
