import React, { useEffect, useState } from "react";

export type NumberInputProps = {
    value: number;
    min: number;
    max: number;
    step: number;
    onValueChange: (val: number) => void;
    disabled?: boolean;
    className?: string;
};

// Number input paired with a slider. Keeps the text field editable while
// the value is also updated from the outside (slider drag, server response).
export const NumberInput = (props: NumberInputProps) => {
    const { value, min, max, step, onValueChange, disabled, className } = props;
    const [text, setText] = useState<string>(String(value));

    useEffect(() => {
        setText(String(value));
    }, [value]);

    return (
        <input
            className={className ?? "slider-value-input"}
            type="number"
            min={min}
            max={max}
            step={step}
            value={text}
            disabled={disabled}
            onChange={(e) => {
                const t = e.target.value;
                setText(t);
                if (t === "" || t === "-") return;
                const v = Number(t);
                if (Number.isNaN(v)) return;
                onValueChange(Math.min(max, Math.max(min, v)));
            }}
            onBlur={() => {
                setText(String(value));
            }}
        />
    );
};
