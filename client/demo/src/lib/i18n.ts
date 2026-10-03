// Minimal re-implementation of the React app's useMessageBuilder.
// Messages are registered as {ja, en} pairs and resolved from the browser
// language, exactly like the original (`navigator.language == "ja"` → ja).

type Message = {
    file: string;
    id: string;
    message: { [lang: string]: string };
};

const registered = new Map<string, Map<string, string>>();

export const registerMessages = (file: string, messages: Record<string, { ja: string; en: string }>) => {
    let byId = registered.get(file);
    if (!byId) {
        byId = new Map();
        registered.set(file, byId);
    }
    for (const [id, msg] of Object.entries(messages)) {
        if (byId.has(id)) {
            console.warn(`duplicate message is registerd: ${file}/${id}`);
        }
        byId.set(id, msg.en);
        // keep ja available for future use
        if (!byId.has(`${id}__ja`)) {
            byId.set(`${id}__ja`, msg.ja);
        }
    }
};

export const getMessage = (file: string, id: string): string => {
    const byId = registered.get(file);
    if (!byId) {
        return "unknwon message";
    }
    const lang = window.navigator.language === "ja" ? "ja" : "en";
    const msg = lang === "ja" ? (byId.get(`${id}__ja`) ?? byId.get(id)) : byId.get(id);
    return msg ?? "unknwon message";
};
