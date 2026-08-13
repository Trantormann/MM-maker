<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
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

// ---- Methods ----
function renderMarkdown(content: string): string {
	try {
		const html = marked.parse(content, { async: false }) as string;
		// 渲染 KaTeX 公式
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
			<!-- 左侧：实时消息 -->
			<div class="messages-panel">
				<h2 class="panel-title">执行进度</h2>
				<div class="progress-section">
					<div class="progress-info">
						<span>总体进度</span>
						<span>{{ taskStore.progress }}%</span>
					</div>
					<div class="progress-track">
						<div
							class="progress-value"
							:style="{ width: taskStore.progress + '%' }"
						></div>
					</div>
				</div>

				<div class="messages-list">
					<div
						v-for="(msg, i) in taskStore.messages"
						:key="i"
						class="message"
						:class="msg.type || 'info'"
					>
						<div class="message-time">
							{{ new Date().toLocaleTimeString() }}
						</div>
						<div class="message-content">
							{{ msg.content || msg.message }}
						</div>
						<div v-if="msg.score !== undefined" class="message-score">
							得分: {{ msg.score }}
						</div>
					</div>

					<div
						v-if="taskStore.messages.length === 0"
						class="empty-state"
					>
						等待任务开始...
					</div>
				</div>

				<!-- HIL 检查点 -->
				<div v-if="taskStore.pendingCheckpoint" class="hil-panel">
					<h3>⚠️ 需要您的决策</h3>
					<p>阶段: {{ taskStore.pendingCheckpoint.stage }}</p>
					<div class="hil-actions">
						<button
							class="hil-btn confirm"
							@click="
								modelingApi.submitHilDecision(
									taskId,
									taskStore.pendingCheckpoint.checkpoint_id!,
									'confirm',
								)
							"
						>
							确认
						</button>
						<button
							class="hil-btn regenerate"
							@click="
								modelingApi.submitHilDecision(
									taskId,
									taskStore.pendingCheckpoint.checkpoint_id!,
									'regenerate',
								)
							"
						>
							重新生成
						</button>
						<button
							class="hil-btn skip"
							@click="
								modelingApi.submitHilDecision(
									taskId,
									taskStore.pendingCheckpoint.checkpoint_id!,
									'skip',
								)
							"
						>
							跳过
						</button>
						<button
							class="hil-btn abort"
							@click="
								modelingApi.submitHilDecision(
									taskId,
									taskStore.pendingCheckpoint.checkpoint_id!,
									'abort',
								)
							"
						>
							中止
						</button>
					</div>
				</div>
			</div>

			<!-- 右侧：论文预览 -->
			<div class="paper-panel">
				<div class="paper-header">
					<h2 class="panel-title">论文预览</h2>
					<button class="load-btn" @click="loadPaper">
						{{ showPaper ? "刷新论文" : "查看论文" }}
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
	grid-template-columns: 380px 1fr;
	gap: 24px;
	height: calc(100vh - 120px);
}

.panel-title {
	font-size: 16px;
	font-weight: 600;
	margin-bottom: 16px;
}

/* 消息面板 */
.messages-panel {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 20px;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.progress-section {
	margin-bottom: 16px;
}

.progress-info {
	display: flex;
	justify-content: space-between;
	font-size: 13px;
	color: var(--text-secondary);
	margin-bottom: 6px;
}

.progress-track {
	height: 8px;
	background: var(--border);
	border-radius: 4px;
	overflow: hidden;
}

.progress-value {
	height: 100%;
	background: var(--primary);
	border-radius: 4px;
	transition: width 0.5s ease;
}

.messages-list {
	flex: 1;
	overflow-y: auto;
}

.message {
	padding: 10px 12px;
	border-radius: 8px;
	margin-bottom: 8px;
	background: var(--bg);
	font-size: 13px;
}

.message.success {
	background: #f0fdf4;
	border-left: 3px solid var(--success);
}

.message.warning {
	background: #fffbeb;
	border-left: 3px solid var(--warning);
}

.message.error {
	background: #fef2f2;
	border-left: 3px solid var(--danger);
}

.message.info {
	border-left: 3px solid var(--primary);
}

.message-time {
	font-size: 11px;
	color: var(--text-secondary);
	margin-bottom: 4px;
}

.message-score {
	font-weight: 600;
	color: var(--primary);
	margin-top: 4px;
}

.empty-state {
	text-align: center;
	color: var(--text-secondary);
	padding: 40px 0;
	font-size: 14px;
}

/* HIL 面板 */
.hil-panel {
	background: #fff7ed;
	border: 1px solid #fed7aa;
	border-radius: 8px;
	padding: 16px;
	margin-top: 16px;
}

.hil-panel h3 {
	font-size: 14px;
	margin-bottom: 8px;
	color: #c2410c;
}

.hil-panel p {
	font-size: 13px;
	margin-bottom: 12px;
}

.hil-actions {
	display: flex;
	gap: 8px;
	flex-wrap: wrap;
}

.hil-btn {
	padding: 8px 16px;
	border-radius: 6px;
	border: none;
	cursor: pointer;
	font-size: 13px;
	font-weight: 500;
	transition: all 0.2s;
}

.hil-btn.confirm {
	background: var(--success);
	color: white;
}

.hil-btn.regenerate {
	background: var(--primary);
	color: white;
}

.hil-btn.skip {
	background: var(--text-secondary);
	color: white;
}

.hil-btn.abort {
	background: var(--danger);
	color: white;
}

/* 论文面板 */
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

.load-btn {
	padding: 8px 16px;
	background: var(--primary);
	color: white;
	border: none;
	border-radius: 6px;
	cursor: pointer;
	font-size: 13px;
}

.paper-content {
	flex: 1;
	overflow-y: auto;
	padding: 20px;
	background: white;
	border: 1px solid var(--border);
	border-radius: 8px;
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
