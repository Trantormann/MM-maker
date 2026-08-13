import { defineStore } from "pinia";
import { ref } from "vue";

export interface ApiConfigItem {
    apiKey: string;
    baseUrl: string;
    modelId: string;
    apiType: string;
    contextWindow: number;
}

export const useSettingsStore = defineStore(
    "settings",
    () => {
        // ---- State ----
        const coordinator = ref<ApiConfigItem>({
            apiKey: "",
            baseUrl: "https://api.openai.com/v1",
            modelId: "",
            apiType: "openai-chat",
            contextWindow: 128000,
        });
        const modeler = ref<ApiConfigItem>({
            apiKey: "",
            baseUrl: "https://api.openai.com/v1",
            modelId: "",
            apiType: "openai-chat",
            contextWindow: 128000,
        });
        const coder = ref<ApiConfigItem>({
            apiKey: "",
            baseUrl: "https://api.openai.com/v1",
            modelId: "",
            apiType: "openai-chat",
            contextWindow: 128000,
        });
        const writer = ref<ApiConfigItem>({
            apiKey: "",
            baseUrl: "https://api.openai.com/v1",
            modelId: "",
            apiType: "openai-chat",
            contextWindow: 128000,
        });
        const reviewer = ref<ApiConfigItem>({
            apiKey: "",
            baseUrl: "https://api.openai.com/v1",
            modelId: "",
            apiType: "openai-chat",
            contextWindow: 128000,
        });
        const openalexEmail = ref("");

        // ---- Actions ----
        function getConfig() {
            return {
                coordinator: coordinator.value,
                modeler: modeler.value,
                coder: coder.value,
                writer: writer.value,
                reviewer: reviewer.value,
                openalex_email: openalexEmail.value,
            };
        }

        return {
            coordinator,
            modeler,
            coder,
            writer,
            reviewer,
            openalexEmail,
            getConfig,
        };
    },
    {
        persist: true,
    },
);
