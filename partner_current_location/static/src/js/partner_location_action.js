/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function partnerCurrentLocationAction(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;

    const partnerId = action.params?.partner_id || action.context?.active_id;

    if (!partnerId) {
        notification.add(_t("ID de contacto no encontrado."), {
            type: "danger",
        });
        return;
    }

    // Notificación de inicio
    notification.add(_t("Obteniendo ubicación actual..."), {
        type: "info",
    });

    let latitude = false;
    let longitude = false;

    try {
        const pos = await new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(_t("Geolocalización no soportada por este navegador.")));
                return;
            }
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0,
            });
        });
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;
    } catch (error) {
        let errorMsg = _t("Error obteniendo ubicación.");
        
        if (error.code === 1) {
            errorMsg = _t("Permiso de ubicación denegado. Por favor, habilita el acceso a la ubicación en tu navegador.");
        } else if (error.code === 2) {
            errorMsg = _t("Ubicación no disponible. Verifica tu conexión GPS/Wi-Fi.");
        } else if (error.code === 3) {
            errorMsg = _t("Tiempo de espera agotado. Intenta nuevamente.");
        }
        
        notification.add(errorMsg, {
            title: _t("Error de Geolocalización"),
            type: "danger",
        });
        return;
    }

    // Guardar coordenadas
    let result = false;
    try {
        result = await orm.call(
            "res.partner",
            "save_current_location",
            [partnerId, latitude, longitude]
        );
    } catch (err) {
        const msg = err.message || String(err);
        notification.add(msg, {
            title: _t("Error al guardar ubicación"),
            type: "danger",
        });
        return;
    }

    // Notificación de éxito
    notification.add(
        _t("Coordenadas guardadas: lat=%(lat)s, lon=%(lon)s", {
            lat: result.latitude.toFixed(6),
            lon: result.longitude.toFixed(6),
        }), {
        title: _t("✓ Ubicación Actualizada"),
        type: "success",
    });

    // Recargar la vista del contacto
    try {
        await actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    } catch (e) {
        console.warn("Reload failed:", e);
    }
}

registry.category("actions").add(
    "partner_current_location.get_location",
    partnerCurrentLocationAction
);