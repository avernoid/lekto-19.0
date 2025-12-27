/* @odoo-module */

import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { TextField } from "@web/views/fields/text/text_field";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Helper component for the reason dialog
class ReasonDialog extends Component {
    static template = "hr_attendance_geolocation_control.ReasonDialog";
    static components = { Dialog };
    setup() {
        this.state = useState({ reason: "" });
    }
    get title() { return _t("Location Reason Required"); }
    get message() { return _t("You are outside the permitted area. Please provide a reason to mark attendance:"); }
    get placeholder() { return _t("Enter reason here..."); }
    get confirmLabel() { return _t("Confirm"); }
    get cancelLabel() { return _t("Cancel"); }
    _confirm() {
        if (!this.state.reason) {
            return;
        }
        this.props.close();
        this.props.onConfirm(this.state.reason);
    }
}

patch(ActivityMenu.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    },
    async signInOut() {
        this.dropdown.close();
        const callBackend = async (data = {}) => {
            try {
                const result = await rpc("/hr_attendance/systray_check_in_out", data);
                if (result && result.location_warning) {
                    this.notification.add(result.location_warning, { type: 'warning' });
                }
                await this.searchReadEmployee();
            } catch (error) {
                if (error && error.data && error.data.message === "GEO_REASON_REQUIRED") {
                    this.dialog.add(ReasonDialog, {
                        onConfirm: async (reason) => {
                            await callBackend({ ...data, out_of_location_reason: reason });
                        }
                    });
                } else {
                    throw error;
                }
            }
        };

        if (!isIosApp() && navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async ({ coords: { latitude, longitude, accuracy } }) => {
                    await callBackend({
                        latitude,
                        longitude,
                        accuracy,
                    });
                },
                async err => {
                    await callBackend();
                },
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0,
                }
            );
        } else {
            await callBackend();
        }
    }
});
