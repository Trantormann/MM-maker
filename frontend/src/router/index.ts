import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
    history: createWebHistory(),
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
