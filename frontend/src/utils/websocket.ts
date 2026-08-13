import { useTaskStore } from "../stores/task";

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private taskId: string;

    constructor(taskId: string) {
        this.taskId = taskId;
    }

    connect() {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const url = `${protocol}://${window.location.host}/ws/${this.taskId}`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log("WebSocket 已连接");
        };

        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const store = useTaskStore();
                store.addMessage(data);
            } catch (e) {
                console.error("WebSocket 消息解析失败", e);
            }
        };

        this.ws.onclose = () => {
            console.log("WebSocket 已断开");
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket 错误", error);
        };
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
