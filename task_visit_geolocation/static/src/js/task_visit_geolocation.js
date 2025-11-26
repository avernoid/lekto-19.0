/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

async function taskVisitGeolocationAction(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;

    const taskId = action.params?.task_id || action.context?.active_id;

    if (!taskId) {
        notification.add(_t("ID de tarea no encontrado."), {
            type: "danger",
        });
        return;
    }

    notification.add(_t("Obteniendo geolocalización..."), {
        type: "info",
    });

    let latitude = false;
    let longitude = false;

    try {
        const pos = await new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(_t("Geolocalización no soportada.")));
                return;
            }
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 8000,
                maximumAge: 0,
            });
        });
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;
    } catch (error) {
        notification.add(error.message, {
            title: _t("Error de Geolocalización"),
            type: "danger",
        });
        return;
    }

    let result = false;
    try {
        result = await orm.call(
            "project.task",
            "action_register_visit_rpc",
            [taskId, latitude, longitude]
        );
    } catch (err) {
        const msg = err.message || String(err);
        notification.add(msg, {
            title: _t("Error al registrar la visita"),
            type: "danger",
        });
        return;
    }

    console.log("RPC Result:", result);

    if (result.allowed) {
        if (result.open_wizard && result.wizard_action) {
            console.log("Opening wizard with action:", result.wizard_action);
            // Show notification about wizard requirement
            notification.add(result.message || _t("Por favor seleccione una razón de pérdida."), {
                title: _t("✓ Visita Registrada"),
                type: "success",
            });
            try {
                await actionService.doAction(result.wizard_action, {
                    onClose: async () => {
                        console.log("Wizard closed, reloading view");
                        await actionService.doAction({
                            type: "ir.actions.act_window",
                            res_model: "project.task",
                            res_id: taskId,
                            views: [[false, "form"]],
                            target: "current",
                            context: action.context,
                        });
                    }
                });
            } catch (e) {
                console.error("Wizard execution failed:", e);
            }
        } else {
            // No wizard needed, just reload
            notification.add(result.message || _t("Visita dentro del rango. Tarea marcada como Hecha."), {
                title: _t("✓ Visita Registrada"),
                type: "success",
            });
            try {
                await actionService.doAction({
                    type: "ir.actions.act_window",
                    res_model: "project.task",
                    res_id: taskId,
                    views: [[false, "form"]],
                    target: "current",
                });
            } catch (e) {
                console.warn("Reload failed:", e);
            }
        }
    } else {
        // Not allowed
        notification.add(result.message || _t("Respuesta desconocida."), {
            title: _t("⚠ No Permitido"),
            type: "warning",
        });
    }
}

registry.category("actions").add(
    "task_visit_geolocation.action_register_visit",
    taskVisitGeolocationAction
);
