/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Field } from "@web/views/fields/field";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

// ============================================
// 1. STUDENT PHOTO WIDGET
// Enhanced image widget with camera capture
// ============================================

export class StudentPhotoWidget extends Component {
    static template = "university_management.StudentPhotoWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.fileInputRef = useRef("fileInput");

        this.placeholder = "/university_management/static/src/img/default_avatar.png";
        this.MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
    }

    get photoUrl() {
        if (this.props.record.data[this.props.name]) {
            return `data:image/png;base64,${this.props.record.data[this.props.name]}`;
        }
        return this.placeholder;
    }

    // Upload button click
    onUploadClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.fileInputRef.el?.click();
    }

    // File input change
    async onFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;

        // Validate file size
        if (file.size > this.MAX_FILE_SIZE) {
            this.notification.add(_t("Please select a file smaller than 5MB"), {
                type: "warning",
                title: _t("File too large"),
            });
            return;
        }

        // Validate file type
        if (!file.type.match("image.*")) {
            this.notification.add(_t("Please select an image file"), {
                type: "warning",
                title: _t("Invalid file type"),
            });
            return;
        }

        // Read and set image
        const reader = new FileReader();
        reader.onload = async (upload) => {
            const data = upload.target.result.split(",")[1];
            await this.props.record.update({ [this.props.name]: data });
        };
        reader.readAsDataURL(file);
    }

    // Camera capture
    async onCameraClick(ev) {
        ev.preventDefault();

        // Check if camera is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.notification.add(
                _t("Your browser does not support camera access"),
                {
                    type: "warning",
                    title: _t("Camera not available"),
                }
            );
            return;
        }

        // Open camera dialog using OWL Dialog service
        this.dialog.add(CameraDialog, {
            onCapture: async (imageData) => {
                await this.props.record.update({ [this.props.name]: imageData });
            },
            notification: this.notification,
        });
    }

    // Remove photo
    async onRemoveClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        await this.props.record.update({ [this.props.name]: false });
    }
}

// ============================================
// Camera Dialog Component
// ============================================

class CameraDialog extends Component {
    static template = "university_management.CameraDialog";
    static props = {
        close: Function,
        onCapture: Function,
        notification: Object,
    };

    setup() {
        this.videoRef = useRef("video");
        this.stream = null;
    }

    async mounted() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
            if (this.videoRef.el) {
                this.videoRef.el.srcObject = this.stream;
                this.videoRef.el.play();
            }
        } catch (err) {
            this.props.notification.add(err.message, {
                type: "danger",
                title: _t("Camera Error"),
            });
            this.props.close();
        }
    }

    willUnmount() {
        // Stop camera
        if (this.stream) {
            this.stream.getTracks().forEach((track) => track.stop());
        }
    }

    onCapture() {
        const video = this.videoRef.el;
        if (video && video.srcObject) {
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0);
            const data = canvas.toDataURL("image/png").split(",")[1];
            this.props.onCapture(data);
        }
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}

// ============================================
// Register Widget
// ============================================

registry.category("fields").add("student_photo", {
    component: StudentPhotoWidget,
});