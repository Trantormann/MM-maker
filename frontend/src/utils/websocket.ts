import { useTaskStore } from "../stores/task";

const HEARTBEAT_INTERVAL = 30_000;
const MAX_RECONNECT_DELAY = 15_000;

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private taskId: string;
    private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private reconnectAttempts = 0;
    private manuallyClosed = false;

    constructor(taskId: string) {
        this.taskId = taskId;
    }

    connect() {
        this.manuallyClosed = false;
        this.open();
    }

    private open() {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const url = `${protocol}://${window.location.host}/ws/${this.taskId}`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log("WebSocket 已连接");
            this.reconnectAttempts = 0;
            this.startHeartbeat();
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
            this.stopHeartbeat();
            if (!this.manuallyClosed) {
                this.scheduleReconnect();
            }
        };

        this.ws.onerror = () => {
            // onclose 会紧随其后触发，由 onclose 统一处理重连
            console.error("WebSocket 连接错误");
        };
    }

    private startHeartbeat() {
        this.stopHeartbeat();
        this.heartbeatTimer = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: "ping" }));
            }
        }, HEARTBEAT_INTERVAL);
    }

    private stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    private scheduleReconnect() {
        if (this.reconnectTimer) return;
        const delay = Math.min(
            1000 * 2 ** this.reconnectAttempts,
            MAX_RECONNECT_DELAY,
        );
        this.reconnectAttempts += 1;
        console.log(
            `WebSocket 将在 ${delay}ms 后重连（第 ${this.reconnectAttempts} 次）`,
        );
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.open();
        }, delay);
    }

    disconnect() {
        this.manuallyClosed = true;
        this.stopHeartbeat();
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
