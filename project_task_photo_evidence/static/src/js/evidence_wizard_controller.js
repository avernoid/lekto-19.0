/** @odoo-module */

import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { onMounted, useState } from "@odoo/owl";

export class EvidenceWizardController extends FormController {
    setup() {
        super.setup();
        this.state = useState({
            locationStatus: "searching", // searching, found, error
            locationMessage: "🛰️ Buscando ubicación...",
        });

        onMounted(() => {
            this._getLocation();
        });
    }

    _getLocation() {
        if (!navigator.geolocation) {
            this.state.locationStatus = "error";
            this.state.locationMessage = "❌ Geolocalización no soportada";
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.state.locationStatus = "found";
                this.state.locationMessage = "✅ Ubicación capturada";
                this._updateCoordinates(position.coords.latitude, position.coords.longitude);
            },
            (error) => {
                console.error("Geolocation error:", error);
                this.state.locationStatus = "error";
                this.state.locationMessage = "❌ Error al obtener ubicación";
            },
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
        );
    }

    async _updateCoordinates(lat, lon) {
        // Write silently to the model field
        // In Odoo 16+ FormController, we interact with the model via props.record or model.root
        // We need to trigger a change in the record so it can be saved.

        // This is a bit tricky in OWL FormController if we want to update the view values.
        // We can use the model's update function.
        if (this.model.root) {
            await this.model.root.update({
                latitude: lat,
                longitude: lon,
            });
        }
    }

    retryLocation() {
        this.state.locationStatus = "searching";
        this.state.locationMessage = "🛰️ Buscando ubicación...";
        this._getLocation();
    }
}

EvidenceWizardController.template = "project_task_photo_evidence.EvidenceWizardController";

export const evidenceWizardView = {
    ...formView,
    Controller: EvidenceWizardController,
};

registry.category("views").add("evidence_geolocation_wizard", evidenceWizardView);
