<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { modelingApi } from "../apis/modelingApi";
import { useTaskStore } from "../stores/task";

const router = useRouter();
const taskStore = useTaskStore();

// ---- State ----
const quesAll = ref("");
const compTemplate = ref("CHINA");
const formatOutput = ref("Markdown");
const files = ref<File[]>([]);
const loading = ref(false);
const error = ref("");
const fileInput = ref<HTMLInputElement | null>(null);

const templates = [
	{ value: "CHINA", label: "国赛", desc: "全国大学生数学建模竞赛" },
	{ value: "AMERICAN", label: "美赛 MCM/ICM", desc: "美国大学生数学建模竞赛" },
	{ value: "HUAWEI", label: "华为杯", desc: "华为杯数学建模竞赛" },
	{ value: "HUASHU", label: "华数杯", desc: "华数杯数学建模竞赛" },
];

// ---- Methods ----
function handleFileSelect(event: Event) {
	const input = event.target as HTMLInputElement;
	if (input.files) {
		files.value = Array.from(input.files);
	}
}

function removeFile(index: number) {
	files.value.splice(index, 1);
}

async function startModeling() {
	if (!quesAll.value.trim()) {
		error.value = "请输入题目内容";
		return;
	}

	loading.value = true;
	error.value = "";

	try {
		const result = await modelingApi.startModeling({
			quesAll: quesAll.value,
			compTemplate: compTemplate.value,
			formatOutput: formatOutput.value,
			files: files.value,
		});

		taskStore.clearMessages();
		taskStore.setTaskId(result.task_id);
		router.push(`/task/${result.task_id}`);
	} catch (e: any) {
		error.value = e.message || "启动任务失败";
	} finally {
		loading.value = false;
	}
}
</script>

<template>
	<div class="home-page">
		<!-- Hero -->
		<div class="hero">
			<div class="hero-badge">🚀 多智能体协作</div>
			<h1>MMmaker</h1>
			<p class="hero-sub">国奖级数学建模竞赛自动化系统</p>
			<p class="hero-desc">
				五大智能体分工协作，从问题拆解、建模设计、代码实现到论文撰写全流程自动化
			</p>
		</div>

		<!-- 建模表单 -->
		<div class="card">
			<!-- 竞赛类型 -->
			<div class="form-group">
				<label class="form-label">竞赛类型</label>
				<div class="template-grid">
					<button
						v-for="tpl in templates"
						:key="tpl.value"
						class="template-card"
						:class="{ active: compTemplate === tpl.value }"
						@click="compTemplate = tpl.value"
					>
						<span class="tpl-label">{{ tpl.label }}</span>
						<span class="tpl-desc">{{ tpl.desc }}</span>
					</button>
				</div>
			</div>

			<!-- 输出格式 -->
			<div class="form-group">
				<label class="form-label">输出格式</label>
				<div class="format-row">
					<button
						class="format-btn"
						:class="{ active: formatOutput === 'Markdown' }"
						@click="formatOutput = 'Markdown'"
					>
						Markdown
					</button>
					<button
						class="format-btn"
						:class="{ active: formatOutput === 'LaTeX' }"
						@click="formatOutput = 'LaTeX'"
					>
						LaTeX
					</button>
				</div>
			</div>

			<!-- 题目内容 -->
			<div class="form-group">
				<label class="form-label">题目内容</label>
				<textarea
					v-model="quesAll"
					class="ques-input"
					rows="10"
					placeholder="请粘贴完整的数学建模题目..."
				></textarea>
				<div class="char-count">{{ quesAll.length }} 字</div>
			</div>

			<!-- 数据文件 -->
			<div class="form-group">
				<label class="form-label">数据文件（可选）</label>
				<div
					class="file-drop-zone"
					@click="fileInput?.click()"
				>
					<input
						ref="fileInput"
						type="file"
						multiple
						@change="handleFileSelect"
						class="file-input"
					/>
					<span class="drop-icon">📎</span>
					<span class="drop-text">点击选择数据文件</span>
				</div>
				<div class="file-list" v-if="files.length > 0">
					<div v-for="(f, i) in files" :key="i" class="file-item">
						<span class="file-name">📄 {{ f.name }}</span>
						<span class="file-size">{{ (f.size / 1024).toFixed(1) }} KB</span>
						<button class="file-remove" @click.stop="removeFile(i)">✕</button>
					</div>
				</div>
			</div>

			<!-- 错误提示 -->
			<div v-if="error" class="error-msg">
				<span>⚠️</span> {{ error }}
			</div>

			<!-- 启动按钮 -->
			<button class="start-btn" :disabled="loading" @click="startModeling">
				<span v-if="loading" class="btn-spinner"></span>
				{{ loading ? "启动中..." : "🚀 开始建模" }}
			</button>
		</div>
	</div>
</template>

<style scoped>
.home-page {
	max-width: 860px;
	margin: 0 auto;
}

/* ---- Hero ---- */
.hero {
	text-align: center;
	padding: 40px 0 32px;
}

.hero-badge {
	display: inline-block;
	padding: 4px 14px;
	background: rgba(37, 99, 235, 0.1);
	color: var(--primary);
	border-radius: 20px;
	font-size: 13px;
	font-weight: 500;
	margin-bottom: 16px;
}

.hero h1 {
	font-size: 44px;
	font-weight: 800;
	background: linear-gradient(135deg, var(--primary), var(--primary-light));
	-webkit-background-clip: text;
	-webkit-text-fill-color: transparent;
	background-clip: text;
	margin-bottom: 8px;
}

.hero-sub {
	font-size: 18px;
	color: var(--text);
	margin-bottom: 8px;
	font-weight: 500;
}

.hero-desc {
	font-size: 14px;
	color: var(--text-secondary);
	max-width: 560px;
	margin: 0 auto;
	line-height: 1.6;
}

/* ---- Card ---- */
.card {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 28px;
	box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.form-group {
	margin-bottom: 24px;
}

.form-label {
	display: block;
	font-size: 14px;
	font-weight: 600;
	margin-bottom: 10px;
	color: var(--text);
}

/* ---- 竞赛类型卡片 ---- */
.template-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 12px;
}

.template-card {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	padding: 14px 16px;
	border: 2px solid var(--border);
	border-radius: 10px;
	background: white;
	cursor: pointer;
	transition: all 0.2s;
	text-align: left;
}

.template-card:hover {
	border-color: var(--primary-light);
	background: rgba(37, 99, 235, 0.02);
}

.template-card.active {
	border-color: var(--primary);
	background: rgba(37, 99, 235, 0.05);
}

.tpl-label {
	font-size: 14px;
	font-weight: 600;
	color: var(--text);
}

.template-card.active .tpl-label {
	color: var(--primary);
}

.tpl-desc {
	font-size: 12px;
	color: var(--text-secondary);
	margin-top: 2px;
}

/* ---- 格式选择 ---- */
.format-row {
	display: flex;
	gap: 10px;
}

.format-btn {
	padding: 10px 24px;
	border: 2px solid var(--border);
	border-radius: 10px;
	background: white;
	cursor: pointer;
	font-size: 14px;
	font-weight: 500;
	transition: all 0.2s;
}

.format-btn:hover {
	border-color: var(--primary-light);
}

.format-btn.active {
	border-color: var(--primary);
	background: var(--primary);
	color: white;
}

/* ---- 题目输入 ---- */
.ques-input {
	width: 100%;
	border: 2px solid var(--border);
	border-radius: 10px;
	padding: 14px;
	font-size: 14px;
	font-family: inherit;
	resize: vertical;
	line-height: 1.6;
	transition: border-color 0.2s;
}

.ques-input:focus {
	outline: none;
	border-color: var(--primary);
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.char-count {
	text-align: right;
	font-size: 12px;
	color: var(--text-secondary);
	margin-top: 4px;
}

/* ---- 文件上传 ---- */
.file-drop-zone {
	border: 2px dashed var(--border);
	border-radius: 10px;
	padding: 24px;
	text-align: center;
	cursor: pointer;
	transition: all 0.2s;
}

.file-drop-zone:hover {
	border-color: var(--primary-light);
	background: rgba(37, 99, 235, 0.02);
}

.file-input {
	display: none;
}

.drop-icon {
	font-size: 24px;
	display: block;
	margin-bottom: 6px;
}

.drop-text {
	font-size: 13px;
	color: var(--text-secondary);
}

.file-list {
	margin-top: 10px;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.file-item {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 12px;
	background: var(--bg);
	border-radius: 8px;
	font-size: 13px;
}

.file-name {
	flex: 1;
	color: var(--text);
}

.file-size {
	color: var(--text-secondary);
	font-size: 12px;
}

.file-remove {
	width: 20px;
	height: 20px;
	border: none;
	background: var(--border);
	color: var(--text-secondary);
	border-radius: 50%;
	cursor: pointer;
	font-size: 11px;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: all 0.2s;
}

.file-remove:hover {
	background: var(--danger);
	color: white;
}

/* ---- 错误提示 ---- */
.error-msg {
	display: flex;
	align-items: center;
	gap: 6px;
	background: #fef2f2;
	color: var(--danger);
	padding: 12px 14px;
	border-radius: 10px;
	margin-bottom: 16px;
	font-size: 14px;
}

/* ---- 启动按钮 ---- */
.start-btn {
	width: 100%;
	padding: 14px;
	background: linear-gradient(135deg, var(--primary), var(--primary-light));
	color: white;
	border: none;
	border-radius: 10px;
	font-size: 16px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
}

.start-btn:hover:not(:disabled) {
	transform: translateY(-1px);
	box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.start-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

.btn-spinner {
	width: 16px;
	height: 16px;
	border: 2px solid rgba(255, 255, 255, 0.3);
	border-top-color: white;
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to { transform: rotate(360deg); }
}
</style>