# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from math import radians, sin, cos, sqrt, atan2

class ProjectProject(models.Model):
    _inherit = "project.project"

    register_geo_visit = fields.Boolean(
        string="Registrar visita con Geolocalización",
        help="Activa el registro de visitas con geolocalización."
    )

    max_distance_m = fields.Float(
        string="Distancia máxima permitida (m)",
        default=100.0,
        help="Distancia en metros permitida entre la geolocalización detectada y la del cliente."
    )


class ProjectTask(models.Model):
    _inherit = "project.task"

    last_latitude = fields.Float(string="Última Latitud", digits=(10, 7), readonly=True)
    last_longitude = fields.Float(string="Última Longitud", digits=(10, 7), readonly=True)
    
    register_geo_visit = fields.Boolean(
        string="Geolocalización Activa",
        related="project_id.register_geo_visit",
        store=True,
        readonly=True
    )

    def action_register_visit(self, *args, **kwargs):
        """
        Método llamado desde el botón 'Registrar visita'.
        Retorna acción cliente que dispara JS para obtener geolocalización.
        """
        self.ensure_one()
        if not self.project_id.register_geo_visit:
            raise UserError(_("Este proyecto no tiene activada la opción de registrar visita con geolocalización."))

        return {
            'type': 'ir.actions.client',
            'tag': 'task_visit_geolocation.action_register_visit',
            'params': {
                'task_id': self.id,
            }
        }

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000  # metros
        d_lat = radians(lat2 - lat1)
        d_lon = radians(lon2 - lon1)

        a = (
            sin(d_lat / 2) ** 2 +
            cos(radians(lat1)) *
            cos(radians(lat2)) *
            sin(d_lon / 2) ** 2
        )
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    @api.model
    def action_register_visit_rpc(self, task_id, lat, lon):
        task = self.env["project.task"].browse(task_id)
        if not task.exists():
            raise UserError(_("Tarea no encontrada."))

        if not task.project_id.register_geo_visit:
            raise UserError(_("Geolocalización no activa para este proyecto."))

        partner = task.partner_id
        if not (partner.partner_latitude and partner.partner_longitude):
            task.message_post(body=_("El cliente no tiene latitud/longitud registrada."))
            return {"allowed": False, "message": _("Cliente sin geolocalización configurada.")}

        distance = task._haversine_distance(
            lat, lon,
            partner.partner_latitude,
            partner.partner_longitude
        )

        task.write({
            "last_latitude": lat,
            "last_longitude": lon
        })

        task.message_post(
            body=_("Visita registrada: lat=%s, lon=%s. Distancia=%s m") % (lat, lon, round(distance, 2))
        )

        if distance > task.project_id.max_distance_m:
            return {
                "allowed": False,
                "message": _("Distancia fuera del rango permitido (%s m).") % round(distance, 2)
            }

        # Check if lost reason is required
        if task._check_lost_reason_required() and not task.lost_reason_id:
            return {
                "allowed": True,
                "message": _("Visita registrada. Por favor seleccione una razón de pérdida."),
                "open_wizard": True,
                "wizard_action": {
                    'type': 'ir.actions.act_window',
                    'name': _('Lost Reason Required'),
                    'res_model': 'project.task.lost.reason.wizard',
                    'views': [[False, 'form']],
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_task_id': task.id,
                        'active_id': task.id,
                        'active_model': 'project.task',
                        'default_from_geo_visit': True,
                    }
                }
            }

        task.write({"state": "1_done"})

        return {
            "allowed": True,
            "message": _("Visita dentro del rango. Tarea marcada como Hecha.")
        }
