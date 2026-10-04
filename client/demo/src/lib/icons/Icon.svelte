<script lang="ts">
    export type IconName =
        | "github"
        | "sort-numeric"
        | "sort-alpha"
        | "warning"
        | "folder"
        | "screen"
        | "refresh"
        | "pencil"
        | "x"
        | "info"
        | "download"
        | "upload"
        | "sliders"
        | "server"
        | "cpu"
        | "trash"
        | "check"
        | "link";

    let { name, size = 16 }: { name: IconName; size?: number } = $props();

    const paths: Record<IconName, string> = {
        github:
            "M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22",
        "sort-numeric": "M4 4v16m0 0-3-3m3 3 3-3M12 5h4l-4 5h4M18 13c-1.5 0-2.5 1-2.5 3s1 3 2.5 3 2.5-1 2.5-3-1-3-2.5-3Z",
        "sort-alpha": "M4 4v16m0 0-3-3m3 3 3-3M12 20h5l-5-9h5m3.5 2c-1.7 0-2.5 1-2.5 2.7 0 2 .8 3.3 2.5 3.3s2.5-1.3 2.5-3.3c0-1.7-.8-2.7-2.5-2.7Z",
        warning: "M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4m0 4h.01",
        folder: "M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z",
        screen: "M2 4a1 1 0 0 1 1-1h18a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1zM8 21h8m-4-5v5",
        refresh: "M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6",
        pencil: "M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Zm-2 4 4 4",
        x: "M18 6 6 18M6 6l12 12",
        info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zm0-16h.01M11 12h1v4h1",
        download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4m4-5 5 5 5-5m-5 5V3",
        upload: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4m4-9 5-5 5 5m-5-5v12",
        sliders: "M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3M1 14h6M9 8h6m2 8h6",
        server: "M4 3h16a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm0 10h16a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1ZM7 6.5h.01M7 16.5h.01",
        cpu: "M5 5h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm4-4v4m6-4v4M9 19v4m6-4v4M3 9h2m-2 6h2m14-6h2m-2 6h2M9 9h6v6H9z",
        trash: "M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14ZM10 11v6m4-6v6",
        check: "M20 6 9 17l-5-5",
        link: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71 M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71",
    };
</script>

<svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    class="shrink-0"
    aria-hidden="true"
>
    <path d={paths[name]} />
</svg>
