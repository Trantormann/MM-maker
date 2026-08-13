import axios from "axios";

const api = axios.create({
    baseURL: "/api",
    timeout: 30000,
});

export interface ApiConfig {
    apiKey: string;
    baseUrl: string;
    modelId: string;
    apiType: string;
    contextWindow: number;
}

export interface StartModelingParams {
    quesAll: string;
    compTemplate: string;
    formatOutput: string;
    files: File[];
}

export const modelingApi = {
    /** 启动建模任务 */
    async startModeling(params: StartModelingParams) {
        const formData = new FormData();
        formData.append("ques_all", params.quesAll);
        formData.append("comp_template", params.compTemplate);
        formData.append("format_output", params.formatOutput);
        for (const file of params.files) {
            formData.append("files", file);
        }
        const response = await api.post("/modeling", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return response.data;
    },

    /** 取消任务 */
    async cancelTask(taskId: string) {
        const response = await api.post(`/modeling/${taskId}/cancel`);
        return response.data;
    },

    /** 获取任务状态 */
    async getTaskStatus(taskId: string) {
        const response = await api.get(`/modeling/${taskId}/status`);
        return response.data;
    },

    /** 获取任务结果 */
    async getTaskResult(taskId: string) {
        const response = await api.get(`/modeling/${taskId}/result`);
        return response.data;
    },

    /** 提交 HIL 决策 */
    async submitHilDecision(
        taskId: string,
        checkpointId: string,
        action: string,
        feedback?: string,
    ) {
        const response = await api.post(`/modeling/${taskId}/hil-decision`, {
            task_id: taskId,
            checkpoint_id: checkpointId,
            action,
            feedback,
        });
        return response.data;
    },

    /** 保存 API 配置 */
    async saveApiConfig(config: {
        coordinator: ApiConfig;
        modeler: ApiConfig;
        coder: ApiConfig;
        writer: ApiConfig;
        reviewer: ApiConfig;
        openalex_email: string;
    }) {
        const response = await api.post("/save-api-config", config);
        return response.data;
    },

    /** 验证 API Key */
    async validateApiKey(params: {
        apiKey: string;
        baseUrl: string;
        modelId: string;
        apiType: string;
    }) {
        const response = await api.post("/validate-api-key", params);
        return response.data;
    },
};
