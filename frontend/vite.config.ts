import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Docker 部署时通过 VITE_API_TARGET 指定后端地址（如 http://backend:8000）
// 本地开发默认使用 http://localhost:8000
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8000";
const wsTarget = apiTarget.replace(/^http/, "ws");

export default defineConfig({
    plugins: [vue()],
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: apiTarget,
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, ""),
            },
            "/ws": {
                target: wsTarget,
                ws: true,
            },
        },
    },
});
