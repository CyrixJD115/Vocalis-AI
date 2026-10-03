// Floating tooltip via a Svelte action. Usage: <span use:tooltip={"hint text"}>
// Only one tooltip element exists at a time (created lazily), mirroring the
// single <Tooltip id="hint"> of the React app.

let tooltipEl: HTMLDivElement | null = null;
let currentTarget: HTMLElement | null = null;

const ensureTooltipEl = () => {
    if (!tooltipEl) {
        tooltipEl = document.createElement("div");
        tooltipEl.className = "vc-tooltip";
        tooltipEl.setAttribute("role", "tooltip");
        document.body.appendChild(tooltipEl);
    }
    return tooltipEl;
};

const show = (target: HTMLElement, text: string) => {
    const el = ensureTooltipEl();
    currentTarget = target;
    el.textContent = text;
    el.classList.add("vc-tooltip-show");
    const rect = target.getBoundingClientRect();
    el.style.left = "0px";
    el.style.top = "0px";
    const elRect = el.getBoundingClientRect();
    let x = rect.left + rect.width / 2 - elRect.width / 2;
    let y = rect.top - elRect.height - 8;
    x = Math.max(8, Math.min(x, window.innerWidth - elRect.width - 8));
    if (y < 8) {
        y = rect.bottom + 8;
    }
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
};

const hide = () => {
    currentTarget = null;
    tooltipEl?.classList.remove("vc-tooltip-show");
};

export const tooltip = (node: HTMLElement, text?: string) => {
    let current = text;
    const onEnter = () => {
        if (current) {
            show(node, current);
        }
    };
    const onLeave = () => hide();
    node.addEventListener("mouseenter", onEnter);
    node.addEventListener("mouseleave", onLeave);
    node.addEventListener("blur", onLeave);
    return {
        update(newText?: string) {
            current = newText;
            if (currentTarget === node) {
                if (current) {
                    show(node, current);
                } else {
                    hide();
                }
            }
        },
        destroy() {
            node.removeEventListener("mouseenter", onEnter);
            node.removeEventListener("mouseleave", onLeave);
            node.removeEventListener("blur", onLeave);
            if (currentTarget === node) {
                hide();
            }
        },
    };
};
