/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ImageCameraField extends Component {
    static template = "project_task_photo_evidence.ImageCameraField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        this.fileInput = useRef("fileInput");
    }

    onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) {
            return;
        }

        const reader = new FileReader();
        reader.onload = () => {
            // result is "data:image/jpeg;base64,....", we need only the base64 part
            const base64Content = reader.result.split(",")[1];
            this.props.record.update({ [this.props.name]: base64Content });
        };
        reader.onerror = () => {
            this.notification.add("Error reading file", { type: "danger" });
        };
        reader.readAsDataURL(file);
    }

    triggerUpload() {
        this.fileInput.el.click();
    }
}

export const imageCameraField = {
    component: ImageCameraField,
    supportedTypes: ["binary"],
};

registry.category("fields").add("image_camera", imageCameraField);
