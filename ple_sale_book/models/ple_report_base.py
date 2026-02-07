from odoo import api, fields, models
from odoo.exceptions import UserError
from lxml import etree
import json


class PleReportBase(models.AbstractModel):
    _name = 'ple.report.base'
    _description = 'Base Books - PLE'

    date_start = fields.Date(
        string='Fecha Inicio',
        required=True
    )
    state = fields.Selection(selection=[
        ('draft', 'Borrador'),
        ('load', 'Generado'),
        ('closed', 'Declarado')], 
        string='Estado', 
        default='draft', 
        required=True
    )
    date_end = fields.Date(
        string='Fecha Fin',
        required=True
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    date_ple = fields.Date(
        string='Generado el',
        readonly=True
    )
    state_send = fields.Selection(
        selection=[
        ('0', 'Cierre de Operaciones - Bajo de Inscripciones en el RUC'),
        ('1', 'Empresa o Entidad Operativa'),
        ('2', 'Cierre de libro - No Obligado a llevarlo')
        ], 
        string='Estado de Envío',
        required=True
    )
    xls_filename = fields.Char(
        string='Filaname Excel'
    )
    xls_binary = fields.Binary(
        string='Reporte Excel'
    )
    txt_filename = fields.Char(
        string='Filaname .TXT'
    )
    txt_binary = fields.Binary(
        string='Reporte .TXT'
    )
    error_dialog = fields.Text(
        readonly=True
    )

    @api.depends('date_start', 'date_end')
    def _compute_display_name(self):
        for obj in self:
            if obj.date_start and obj.date_end:
                obj.display_name = '%s - %s' % (obj.date_start.strftime('%d/%m/%Y'), obj.date_end.strftime('%d/%m/%Y'))
            else:
                obj.display_name = ''


    @staticmethod
    def validate_string(value, max_len=-1):
        """Check string composition to avoid errors when it is sended to SUNAT.

        :param value: String value.
        :param max_len: Máx legth permitted.

        :return: Formatted resized string.
        """
        if value:
            if value.find('–') != -1:
                value = value.replace("–", " ")
            if value.find('/') != -1:
                value = value.replace("/", " ")
            if value.find('\n') != -1:
                value = value.replace('\n', ' ')
            if value.find('&') != -1:
                value = value.replace('&', '&amp;')
            if value.find('á') != -1:
                value = value.replace('á', 'a')
            if value.find('é') != -1:
                value = value.replace('é', 'e')
            if value.find('í') != -1:
                value = value.replace('í', 'i')
            if value.find('ó') != -1:
                value = value.replace('ó', 'o')
            if value.find('ú') != -1:
                value = value.replace('ú', 'u')
            if max_len != -1:
                return value[:max_len]
        return ''

    @staticmethod
    def check_decimals(value):
        """Check if string number has two decimals else it will fill up with zeros.

        :param value: String value.

        :return: Formatted string number with two decimals.
        """
        value = str(float('%.2f' % value))
        if not len(value.rsplit('.')[-1]) == 2:
            value += '0'
        return value

    def action_generate_report(self):
        pass

    def action_generate_excel(self):
        pass

    def action_close(self):
        self.ensure_one()
        self.write({'state': 'closed'})

    def action_rollback(self):
        self.write({'state': 'draft'})

    def unlink(self):
        for record in self:
            if record.state == 'closed':
                raise UserError('Regrese a estado borrador para revertir y permitir eliminar.')
        return super(PleReportBase, self).unlink()