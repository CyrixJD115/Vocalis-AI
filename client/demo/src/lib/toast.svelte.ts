import { registerMessages } from "./i18n";

registerMessages("toast", {});

export type ToastKind = "info" | "success" | "warn" | "error";

export type Toast = {
    id: number;
    kind: ToastKind;
    message: string;
    leaving: boolean;
};

let nextId = 1;

class ToastState {
    toasts = $state<Toast[]>([]);
    #timers = new Map<number, ReturnType<typeof setTimeout>[]>();

    show(kind: ToastKind, message: string, duration = 4000) {
        const id = nextId++;
        this.toasts.push({ id, kind, message, leaving: false });
        const t1 = setTimeout(() => {
            const toast = this.toasts.find((t) => t.id === id);
            if (toast) {
                toast.leaving = true;
            }
        }, duration);
        const t2 = setTimeout(() => {
            this.toasts = this.toasts.filter((t) => t.id !== id);
            this.#timers.delete(id);
        }, duration + 300);
        this.#timers.set(id, [t1, t2]);
    }

    info(message: string) {
        this.show("info", message);
    }
    success(message: string) {
        this.show("success", message);
    }
    warn(message: string) {
        this.show("warn", message);
    }
    error(message: string) {
        this.show("error", message, 6000);
    }
}

export const toastState = new ToastState();

export const toast = {
    info: (m: string) => toastState.info(m),
    success: (m: string) => toastState.success(m),
    warn: (m: string) => toastState.warn(m),
    error: (m: string) => toastState.error(m),
};
