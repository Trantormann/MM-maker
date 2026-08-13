<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { marked } from "marked";
import katex from "katex";
import "katex/dist/katex.min.css";
import { modelingApi } from "../apis/modelingApi";
import { useTaskStore } from "../stores/task";
import { WebSocketClient } from "../utils/websocket";

const route = useRoute();
const taskStore = useTaskStore();
const taskId = route.params.taskId as string;

let wsClient: WebSocketClient | null = null;
const paperContent = ref("");
const showPaper = ref(false);
const autoScroll = ref(true);

// ---- 阶段定义 ----
const stages = [
	{ key: "init", label: "初始化", icon: "⚙️" },
	{ key: "coordinator", label: "问题拆解", icon: "🔍" },
	{ key: "modeler", label: "建模设计", icon: "📐" },
	{ key: "solve", label: "代码求解", icon: "💻" },
	{ key: "write", label: "论文撰写", icon: "✍️" },
	{ key: "done", label: "完成", icon: "✅" },
];

const currentStageIndex = computed(() => {
	const idx = stages.findIndex((s) => s.key === taskStore.currentStage);
	return idx >= 0 ? idx : 0;
});

const isRunning = computed(() => taskStore.status === "running");
const isCompleted = computed(() => taskStore.status === "completed");

// ---- Methods ----
function renderMarkdown(content: string): string {
	try {
		const html = marked.parse(content, { async: false }) as string;
		return html.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g, (match, block, inline) => {
			const tex = block || inline;
			try {
				return katex.renderToString(tex, {
					displayMode: !!block,
					throwOnError: false,
				});
			} catch {
				return match;
			}
		});
	} catch {
		return content;
	}
}

async function loadPaper() {
	try {
		const result = await modelingApi.getTaskResult(taskId);
		paperContent.value = result.content;
		showPaper.value = true;
	} catch (e) {
		console.error("加载论文失败", e);
	}
}

function scrollToBottom() {
	if (!autoScroll.value) return;
	const list = document.querySelector(".messages-list");
	if (list) list.scrollTop = list.scrollHeight;
}

watch(
	() => taskStore.messages.length,
	() => {
		setTimeout(scrollToBottom, 50);
	},
);

onMounted(() => {
	taskStore.clearMessages();
	taskStore.setTaskId(taskId);
	wsClient = new WebSocketClient(taskId);
	wsClient.connect();
});

onUnmounted(() => {
	wsClient?.disconnect();
});
</script>

<template>
	<div class="task-page">
		<div class="task-layout">
			<!-- 左侧：进度面板 -->
			<div class="progress-panel">
				<!-- 总体进度 -->
				<div class="overall-progress">
					<div class="progress-header">
						<span class="progress-title">总体进度</span>
						<span class="progress-percent">{{ Math.round(taskStore.progress) }}%</span>
					</div>
					<div class="progress-bar-track">
						<div
							class="progress-bar-fill"
							:class="{ completed: isCompleted, running: isRunning }"
							:style="{ width: taskStore.progress + '%' }"
						>
							<div v-if="isRunning" class="progress-shimmer"></div>
						</div>
					</div>
				</div>

				<!-- 阶段步骤 -->
				<div class="stage-steps">
					<div
						v-for="(stage, i) in stages"
						:key="stage.key"
						class="stage-step"
						:class="{
							active: i === currentStageIndex && isRunning,
							done: i < currentStageIndex || isCompleted,
							pending: i > currentStageIndex,
						}"
					>
						<div class="stage-icon">
							<span v-if="i < currentStageIndex || isCompleted" class="check">✓</span>
							<span v-else-if="i === currentStageIndex && isRunning" class="spinner"></span>
							<span v-else>{{ stage.icon }}</span>
						</div>
						<div class="stage-info">
							<span class="stage-label">{{ stage.label }}</span>
							<span v-if="i === currentStageIndex && isRunning" class="stage-status">
								进行中...
							</span>
						</div>
					</div>
				</div>

				<!-- 实时消息 -->
				<div class="messages-section">
					<div class="messages-header">
						<span>实时日志</span>
						<label class="auto-scroll-toggle">
							<input type="checkbox" v-model="autoScroll" />
							自动滚动
						</label>
					</div>
					<div class="messages-list">
						<div
							v-for="(msg, i) in taskStore.messages"
							:key="i"
							class="log-entry"
							:class="msg.type || 'info'"
						>
							<span class="log-dot"></span>
							<span class="log-text">{{ msg.content || msg.message }}</span>
							<span v-if="msg.score !== undefined" class="log-score">
								得分: {{ msg.score }}
							</span>
						</div>
						<div v-if="taskStore.messages.length === 0" class="empty-state">
							<div class="empty-icon">⏳</div>
							<p>等待任务开始...</p>
						</div>
					</div>
				</div>
			</div>

			<!-- 右侧：论文预览 -->
			<div class="paper-panel">
				<div class="paper-header">
					<h2 class="panel-title">论文预览</h2>
					<button class="load-btn" :class="{ active: showPaper }" @click="loadPaper">
						{{ showPaper ? "🔄 刷新" : "📄 查看论文" }}
					</button>
				</div>
				<div v-if="showPaper" class="paper-content" v-html="renderMarkdown(paperContent)"></div>
				<div v-else class="paper-placeholder">
					<div class="placeholder-icon">📄</div>
					<p>任务完成后点击"查看论文"预览生成的论文</p>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.task-page {
	max-width: 1400px;
	margin: 0 auto;
}

.task-layout {
	display: grid;
	grid-template-columns: 400px 1fr;
	gap: 20px;
	height: calc(100vh - 120px);
}

/* ---- 进度面板 ---- */
.progress-panel {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 20px;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.overall-progress {
	margin-bottom: 20px;
}

.progress-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 8px;
}

.progress-title {
	font-size: 14px;
	font-weight: 600;
	color: var(--text);
}

.progress-percent {
	font-size: 20px;
	font-weight: 700;
	color: var(--primary);
}

.progress-bar-track {
	height: 10px;
	background: var(--border);
	border-radius: 6px;
	overflow: hidden;
	position: relative;
}

.progress-bar-fill {
	height: 100%;
	border-radius: 6px;
	transition: width 0.6s ease;
	position: relative;
	overflow: hidden;
}

.progress-bar-fill.running {
	background: linear-gradient(90deg, var(--primary), var(--primary-light));
}

.progress-bar-fill.completed {
	background: var(--success);
}

.progress-shimmer {
	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	background: linear-gradient(
		90deg,
		transparent,
		rgba(255, 255, 255, 0.3),
		transparent
	);
	animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
	0% { transform: translateX(-100%); }
	100% { transform: translateX(100%); }
}

/* ---- 阶段步骤 ---- */
.stage-steps {
	display: flex;
	flex-direction: column;
	gap: 4px;
	margin-bottom: 20px;
	padding: 16px;
	background: var(--bg);
	border-radius: 10px;
}

.stage-step {
	display: flex;
	align-items: center;
	gap: 12px;
	padding: 8px 10px;
	border-radius: 8px;
	transition: all 0.3s;
}

.stage-step.active {
	background: rgba(37, 99, 235, 0.08);
}

.stage-step.done {
	opacity: 0.6;
}

.stage-icon {
	width: 28px;
	height: 28px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
	flex-shrink: 0;
	background: var(--border);
}

.stage-step.active .stage-icon {
	background: var(--primary);
	color: white;
}

.stage-step.done .stage-icon {
	background: var(--success);
	color: white;
}

.stage-step.done .check {
	font-size: 14px;
	font-weight: 700;
}

.spinner {
	width: 14px;
	height: 14px;
	border: 2px solid rgba(255, 255, 255, 0.3);
	border-top-color: white;
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to { transform: rotate(360deg); }
}

.stage-info {
	display: flex;
	flex-direction: column;
}

.stage-label {
	font-size: 13px;
	font-weight: 500;
	color: var(--text);
}

.stage-step.active .stage-label {
	color: var(--primary);
	font-weight: 600;
}

.stage-status {
	font-size: 11px;
	color: var(--primary);
}

/* ---- 消息日志 ---- */
.messages-section {
	flex: 1;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.messages-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	font-size: 13px;
	font-weight: 600;
	color: var(--text-secondary);
	margin-bottom: 10px;
}

.auto-scroll-toggle {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 11px;
	font-weight: 400;
	cursor: pointer;
}

.auto-scroll-toggle input {
	width: 14px;
	height: 14px;
}

.messages-list {
	flex: 1;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.log-entry {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	padding: 6px 10px;
	border-radius: 6px;
	font-size: 12px;
	line-height: 1.5;
	color: var(--text-secondary);
	transition: background 0.2s;
}

.log-entry:hover {
	background: var(--bg);
}

.log-dot {
	width: 6px;
	height: 6px;
	border-radius: 50%;
	margin-top: 6px;
	flex-shrink: 0;
	background: var(--text-secondary);
}

.log-entry.success .log-dot {
	background: var(--success);
}

.log-entry.success {
	color: var(--success);
}

.log-entry.warning .log-dot {
	background: var(--warning);
}

.log-entry.error .log-dot {
	background: var(--danger);
}

.log-entry.error {
	color: var(--danger);
}

.log-entry.info .log-dot {
	background: var(--primary);
}

.log-entry.info {
	color: var(--text);
}

.log-text {
	flex: 1;
}

.log-score {
	font-weight: 600;
	color: var(--primary);
}

.empty-state {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	color: var(--text-secondary);
}

.empty-icon {
	font-size: 36px;
	margin-bottom: 8px;
}

/* ---- 论文面板 ---- */
.paper-panel {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 20px;
	overflow: hidden;
	display: flex;
	flex-direction: column;
}

.paper-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16px;
}

.panel-title {
	font-size: 16px;
	font-weight: 600;
}

.load-btn {
	padding: 8px 16px;
	background: var(--primary);
	color: white;
	border: none;
	border-radius: 8px;
	cursor: pointer;
	font-size: 13px;
	font-weight: 500;
	transition: all 0.2s;
}

.load-btn:hover {
	background: var(--primary-dark);
}

.load-btn.active {
	background: var(--text-secondary);
}

.paper-content {
	flex: 1;
	overflow-y: auto;
	padding: 24px;
	background: white;
	border: 1px solid var(--border);
	border-radius: 10px;
	line-height: 1.8;
	font-size: 14px;
}

.paper-content :deep(h1),
.paper-content :deep(h2),
.paper-content :deep(h3) {
	margin: 16px 0 8px;
}

.paper-content :deep(img) {
	max-width: 100%;
	border-radius: 8px;
	margin: 12px 0;
}

.paper-content :deep(table) {
	border-collapse: collapse;
	width: 100%;
	margin: 12px 0;
}

.paper-content :deep(td),
.paper-content :deep(th) {
	border: 1px solid var(--border);
	padding: 8px;
}

.paper-placeholder {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	color: var(--text-secondary);
}

.placeholder-icon {
	font-size: 48px;
	margin-bottom: 16px;
}
</style>