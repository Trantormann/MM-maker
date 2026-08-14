import { defineStore } from "pinia";
import { ref } from "vue";

export interface TaskMessage {
    content?: string;
    type?: string;
    task_id?: string;
    status?: string;
    progress?: number;
    current_stage?: string;
    message?: string;
    score?: number;
    checkpoint_id?: string;
    stage?: string;
    content_obj?: Record<string, unknown>;
}

export const useTaskStore = defineStore("task", () => {
    // ---- State ----
    const currentTaskId = ref<string>("");
    const messages = ref<TaskMessage[]>([]);
    const progress = ref(0);
    const status = ref("idle"); // idle | running | completed | error
    const currentStage = ref("");
    const pendingCheckpoint = ref<TaskMessage | null>(null);

    // ---- Actions ----
    function setTaskId(taskId: string) {
        currentTaskId.value = taskId;
    }

    function addMessage(message: TaskMessage) {
        // HIL 检查点消息：捕获待审批检查点，同时生成一条可读日志
        if (message.checkpoint_id && message.stage) {
            pendingCheckpoint.value = message;
            messages.value.push({
                content: `等待审批：${message.stage}`,
                type: "warning",
            });
            return;
        }

        messages.value.push(message);
        // 处理不同类型消息
        if (message.status) {
            status.value = message.status;
        }
        if (message.progress !== undefined) {
            progress.value = message.progress;
        }
        if (message.current_stage) {
            currentStage.value = message.current_stage;
        }
    }

    function clearMessages() {
        messages.value = [];
        progress.value = 0;
        status.value = "idle";
        currentStage.value = "";
        pendingCheckpoint.value = null;
    }

    return {
        currentTaskId,
        messages,
        progress,
        status,
        currentStage,
        pendingCheckpoint,
        setTaskId,
        addMessage,
        clearMessages,
    };
});
