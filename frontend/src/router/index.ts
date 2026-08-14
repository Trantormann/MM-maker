import { createRouter, createWebHashHistory } from "vue-router";

const router = createRouter({
    // hash 模式：生产环境由 FastAPI 单进程托管静态文件时，
    // 刷新 /task/xxx 等子路由不会因后端无对应路由而 404。
    history: createWebHashHistory(),
    routes: [
        {
            path: "/",
            name: "home",
            component: () => import("../pages/HomePage.vue"),
        },
        {
            path: "/task/:taskId",
            name: "task",
            component: () => import("../pages/TaskPage.vue"),
        },
        {
            path: "/settings",
            name: "settings",
            component: () => import("../pages/SettingsPage.vue"),
        },
    ],
});

export default router;
