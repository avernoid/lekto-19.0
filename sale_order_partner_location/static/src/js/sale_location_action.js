/** @odoo-module **/
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

/**
 * Actualiza la ubicación del partner desde la ubicación actual del dispositivo
 */
async function updatePartnerLocationFromSale(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;

    const saleOrderId = action.params?.sale_order_id;
    const partnerId = action.params?.partner_id;

    if (!saleOrderId || !partnerId) {
        notification.add(_t("Sale order or partner ID not found."), {
            type: "danger",
        });
        return;
    }

    notification.add(_t("Getting your current location..."), {
        type: "info",
    });

    let latitude = false;
    let longitude = false;

    try {
        const pos = await new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(_t("Geolocation is not supported by your browser.")));
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
        let errorMsg = _t("Error getting location.");
        
        if (error.code === 1) {
            errorMsg = _t("Permission denied. Please allow location access in your browser.");
        } else if (error.code === 2) {
            errorMsg = _t("Location unavailable. Check your GPS/Wi-Fi connection.");
        } else if (error.code === 3) {
            errorMsg = _t("Request timeout. Please try again.");
        }
        
        notification.add(errorMsg, {
            title: _t("Geolocation Error"),
            type: "danger",
        });
        return;
    }

    try {
        await orm.call(
            "sale.order",
            "save_partner_location",
            [saleOrderId, latitude, longitude]
        );

        notification.add(_t("Partner location updated successfully."), {
            title: _t("✓ Success"),
            type: "success",
        });

        // Reload the view
        await actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: saleOrderId,
            views: [[false, "form"]],
            target: "current",
        });
    } catch (err) {
        const msg = err.message || String(err);
        notification.add(msg, {
            title: _t("Error saving partner location"),
            type: "danger",
        });
    }
}

/**
 * Registra la ubicación de la venta desde la ubicación actual del dispositivo
 */
async function registerSaleLocation(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;

    const saleOrderId = action.params?.sale_order_id;

    if (!saleOrderId) {
        notification.add(_t("Sale order ID not found."), {
            type: "danger",
        });
        return;
    }

    notification.add(_t("Getting your current location..."), {
        type: "info",
    });

    let latitude = false;
    let longitude = false;

    try {
        const pos = await new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(_t("Geolocation is not supported by your browser.")));
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
        let errorMsg = _t("Error getting location.");
        
        if (error.code === 1) {
            errorMsg = _t("Permission denied. Please allow location access in your browser.");
        } else if (error.code === 2) {
            errorMsg = _t("Location unavailable. Check your GPS/Wi-Fi connection.");
        } else if (error.code === 3) {
            errorMsg = _t("Request timeout. Please try again.");
        }
        
        notification.add(errorMsg, {
            title: _t("Geolocation Error"),
            type: "danger",
        });
        return;
    }

    try {
        await orm.call(
            "sale.order",
            "save_sale_location",
            [saleOrderId, latitude, longitude]
        );

        notification.add(_t("Sale location registered successfully."), {
            title: _t("✓ Success"),
            type: "success",
        });

        // Reload the view
        await actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: saleOrderId,
            views: [[false, "form"]],
            target: "current",
        });
    } catch (err) {
        const msg = err.message || String(err);
        notification.add(msg, {
            title: _t("Error saving sale location"),
            type: "danger",
        });
    }
}

/**
 * Captura ubicación antes de confirmar la orden de venta
 */
async function captureLocationBeforeConfirm(env, action) {
    const orm = env.services.orm;
    const notification = env.services.notification;
    const actionService = env.services.action;
    const dialog = env.services.dialog;

    const saleOrderId = action.params?.sale_order_id;

    if (!saleOrderId) {
        notification.add(_t("Sale order ID not found."), {
            type: "danger",
        });
        return;
    }

    // Función para confirmar sin ubicación
    const confirmWithoutLocation = async () => {
        try {
            await orm.call(
                "sale.order",
                "confirm_without_location",
                [[saleOrderId]]
            );

            notification.add(_t("Sale order confirmed successfully."), {
                title: _t("✓ Confirmed"),
                type: "success",
            });

            await actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "sale.order",
                res_id: saleOrderId,
                views: [[false, "form"]],
                target: "current",
            });
        } catch (err) {
            const msg = err.message || String(err);
            notification.add(msg, {
                title: _t("Error confirming sale order"),
                type: "danger",
            });
        }
    };

    // Verificar si la geolocalización está disponible
    if (!navigator.geolocation) {
        dialog.add(ConfirmationDialog, {
            title: _t("Location Not Available"),
            body: _t("Geolocation is not supported by your browser. Do you want to confirm the sale without location?"),
            confirm: confirmWithoutLocation,
            cancel: () => {},
            confirmLabel: _t("Confirm Without Location"),
            cancelLabel: _t("Cancel"),
        });
        return;
    }

    notification.add(_t("Getting your location to confirm the sale..."), {
        type: "info",
    });

    let latitude = false;
    let longitude = false;

    try {
        const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0,
            });
        });
        latitude = pos.coords.latitude;
        longitude = pos.coords.longitude;
    } catch (error) {
        let errorMsg = _t("Error getting location: ");
        
        if (error.code === 1) {
            errorMsg += _t("Permission denied.");
        } else if (error.code === 2) {
            errorMsg += _t("Location unavailable.");
        } else if (error.code === 3) {
            errorMsg += _t("Request timeout.");
        } else {
            errorMsg += _t("Unknown error.");
        }

        // Preguntar si desea confirmar sin ubicación
        dialog.add(ConfirmationDialog, {
            title: _t("Location Error"),
            body: errorMsg + "\n\n" + _t("Do you want to confirm the sale without location?"),
            confirm: confirmWithoutLocation,
            cancel: () => {},
            confirmLabel: _t("Confirm Without Location"),
            cancelLabel: _t("Cancel"),
        });
        return;
    }

    // Confirmar con ubicación
    try {
        await orm.call(
            "sale.order",
            "confirm_with_location",
            [[saleOrderId], latitude, longitude]
        );

        notification.add(_t("Sale order confirmed with location."), {
            title: _t("✓ Confirmed"),
            type: "success",
        });

        await actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: saleOrderId,
            views: [[false, "form"]],
            target: "current",
        });
    } catch (err) {
        const msg = err.message || String(err);
        notification.add(msg, {
            title: _t("Error confirming sale order"),
            type: "danger",
        });
    }
}

// Registrar las acciones
registry.category("actions").add("update_partner_location_from_sale", updatePartnerLocationFromSale);
registry.category("actions").add("register_sale_location", registerSaleLocation);
registry.category("actions").add("capture_location_before_confirm", captureLocationBeforeConfirm);