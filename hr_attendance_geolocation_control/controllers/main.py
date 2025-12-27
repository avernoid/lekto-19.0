# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.hr_attendance.controllers.main import HrAttendance as NativeHrAttendance

class HrAttendance(NativeHrAttendance):

    def _get_geoip_response(self, mode, latitude=False, longitude=False, **kwargs):
        res = super()._get_geoip_response(mode, latitude, longitude)
        # Add accuracy to the geoip response so it reaches the model
        if 'accuracy' in kwargs:
            res['accuracy'] = kwargs['accuracy']
        if 'out_of_location_reason' in kwargs:
            res['out_of_location_reason'] = kwargs['out_of_location_reason']
        return res

    @http.route('/hr_attendance/systray_check_in_out', type="jsonrpc", auth="user")
    def systray_attendance(self, latitude=False, longitude=False, **kwargs):
        employee = request.env.user.employee_id
        geo_ip_response = self._get_geoip_response(mode='systray',
                                                  latitude=latitude,
                                                  longitude=longitude,
                                                  **kwargs)
        employee._attendance_action_change(geo_ip_response)
        
        response = self._get_employee_info_response(employee)
        
        # Check for "Allow with Warning" condition
        last_attendance = employee.last_attendance_id
        if last_attendance and last_attendance.location_reliability == 'low':
             company = employee.company_id
             config = request.env['hr.attendance']._get_effective_config(employee, company)
             if config['accuracy_policy'] == 'warn':
                 response['location_warning'] = _("Warning: Location accuracy is low. Attendance marked.")
                 
        return response

    @http.route('/hr_attendance/manual_selection', type="jsonrpc", auth="public")
    def manual_selection_with_geolocation(self, token, employee_id, pin_code, latitude=False, longitude=False, **kwargs):
        company = self._get_company(token)
        if company:
            employee = request.env['hr.employee'].sudo().browse(employee_id)
            if employee.company_id == company and ((not company.attendance_kiosk_use_pin) or (employee.pin == pin_code)):
                geo_ip_response = self._get_geoip_response('kiosk', latitude=latitude, longitude=longitude, **kwargs)
                employee.sudo()._attendance_action_change(geo_ip_response)
                return self._get_employee_info_response(employee)
        return {}
