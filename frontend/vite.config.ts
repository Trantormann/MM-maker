import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// 后端地址：本地开发默认 http://localhost:8000
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8000";
const wsTarget = apiTarget.replace(/^http/, "ws");

export default defineConfig({
    plugins: [vue()],
    server: {
        port: 5173,
        proxy: {
            // 前端同源直连后端路径（无 /api 前缀），开发模式由 vite 转发，
            // 生产模式由 FastAPI 单进程托管前端静态文件后直接同源命中。
            "/modeling": { target: apiTarget, changeOrigin: true },
            "/save-api-config": { target: apiTarget, changeOrigin: true },
            "/validate-api-key": { target: apiTarget, changeOrigin: true },
            "/files": { target: apiTarget, changeOrigin: true },
            "/health": { target: apiTarget, changeOrigin: true },
            "/ws": { target: wsTarget, ws: true },
        },
    },
});
