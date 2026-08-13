<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useTaskStore } from "./stores/task";

const router = useRouter();
const taskStore = useTaskStore();

const stageLabel = computed(() => {
	const stage = taskStore.currentStage;
	const labels: Record<string, string> = {
		init: "初始化",
		coordinator: "问题拆解",
		modeler: "建模设计",
		solve: "求解中",
		write: "写作中",
		done: "完成",
	};
	return labels[stage] || stage || "等待开始";
});
</script>

<template>
	<div class="app-shell">
		<header class="topbar">
			<div class="brand" @click="router.push('/')">
				<span class="logo">📐</span>
				<span class="title">MMmaker</span>
				<span class="subtitle">国奖级数学建模竞赛自动化系统</span>
			</div>
			<nav class="nav">
				<router-link to="/" class="nav-link">首页</router-link>
				<router-link to="/settings" class="nav-link">设置</router-link>
			</nav>
			<div class="stage-indicator" v-if="taskStore.currentTaskId">
				<span class="stage-dot" :class="taskStore.status"></span>
				<span class="stage-text">{{ stageLabel }}</span>
				<div class="progress-bar">
					<div class="progress-fill" :style="{ width: taskStore.progress + '%' }"></div>
				</div>
			</div>
		</header>
		<main class="content">
			<router-view />
		</main>
	</div>
</template>

<style scoped>
.app-shell {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.topbar {
	display: flex;
	align-items: center;
	gap: 24px;
	padding: 12px 24px;
	background: var(--bg-card);
	border-bottom: 1px solid var(--border);
}

.brand {
	display: flex;
	align-items: center;
	gap: 8px;
	cursor: pointer;
	user-select: none;
}

.logo {
	font-size: 24px;
}

.title {
	font-size: 20px;
	font-weight: 700;
	color: var(--primary);
}

.subtitle {
	font-size: 13px;
	color: var(--text-secondary);
}

.nav {
	display: flex;
	gap: 16px;
	flex: 1;
}

.nav-link {
	text-decoration: none;
	color: var(--text-secondary);
	font-size: 14px;
	padding: 6px 12px;
	border-radius: 8px;
	transition: all 0.2s;
}

.nav-link:hover {
	background: var(--bg);
	color: var(--text);
}

.nav-link.router-link-active {
	background: var(--primary);
	color: white;
}

.stage-indicator {
	display: flex;
	align-items: center;
	gap: 8px;
}

.stage-dot {
	width: 10px;
	height: 10px;
	border-radius: 50%;
	background: var(--text-secondary);
}

.stage-dot.running {
	background: var(--primary);
	animation: pulse 1.5s infinite;
}

.stage-dot.completed {
	background: var(--success);
}

.stage-dot.error {
	background: var(--danger);
}

@keyframes pulse {
	0%,
	100% {
		opacity: 1;
	}
	50% {
		opacity: 0.4;
	}
}

.stage-text {
	font-size: 13px;
	color: var(--text-secondary);
}

.progress-bar {
	width: 100px;
	height: 6px;
	background: var(--border);
	border-radius: 3px;
	overflow: hidden;
}

.progress-fill {
	height: 100%;
	background: var(--primary);
	border-radius: 3px;
	transition: width 0.5s ease;
}

.content {
	flex: 1;
	overflow: auto;
	padding: 24px;
}
</style>
