from io import BytesIO
import xlsxwriter


class ReportInvBalExcel(object):

    def __init__(self, obj, data):
        self.obj = obj
        self.data = data

    def get_content(self):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        style1 = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'size': 10,
            'bold': True,
            'font_name': 'Arial'
        })
        style_number = workbook.add_format({
            'size': 11,
            'num_format': '#,##0.00',
        })

        ws = workbook.add_worksheet('Report EEFF')
        ws.set_column('A:E', 10)

        ws.set_row(0, 50)
        headers = ['Periodo', 'Código del catálogo', 'Código del Rubro del Estado Financiero', 'Nombre de la cuenta contable', 'Saldo del Rubro Contable', 'Indica el estado de la operación']
        ws.write_row(0, 0, headers, style1)

        for i, value in enumerate(self.data, start=1):
            ws.write_row(i, 0, [value['name'], value['catalog_code'], value['financial_state_code'], value['description'], value['real_credit'], value['state']], style_number)

        workbook.close()
        output.seek(0)
        return output.read()

    def get_filename(self):
        year_month = self.obj.date_end.strftime('%Y%m')
        return 'Libro_Estado de Situación Financiera_{}.xlsx'.format(year_month)


class ReportInvBalTxt(object):

    def __init__(self, obj, data):
        self.obj = obj
        self.data = data

    def get_content(self):
        raw = ''
        template = '{name}|{catalog_code}|{financial_state_code}|{credit}|{state}|\r\n'

        for value in self.data:
            raw += template.format(
                name=value['name'],
                catalog_code=value['catalog_code'],
                financial_state_code=value['financial_state_code'],
                credit="{:.2f}".format(value['real_credit']),
                state=value['state'],
            )
        return raw

    def get_filename(self):
        year, month, day = self.obj.date_end.strftime('%Y/%m/%d').split('/')
        return 'LE{vat}{period_year}{period_month}{period_day}030100{eeff_oportunity}{state_send}{has_info}11.txt'.format(
            vat=self.obj.company_id.vat,
            period_year=year,
            period_month=month,
            period_day=day,
            eeff_oportunity=self.obj.eeff_presentation_opportunity,
            state_send=self.obj.state_send or '',
            has_info=int(bool(self.data))
        )
