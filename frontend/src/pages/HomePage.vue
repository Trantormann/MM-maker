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
	{ value: "CHINA", label: "国赛" },
	{ value: "AMERICAN", label: "美赛 MCM/ICM" },
	{ value: "HUAWEI", label: "华为杯" },
	{ value: "HUASHU", label: "华数杯" },
];

// ---- Methods ----
function handleFileSelect(event: Event) {
	const input = event.target as HTMLInputElement;
	if (input.files) {
		files.value = Array.from(input.files);
	}
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
		<div class="hero">
			<h1>MMmaker</h1>
			<p class="hero-sub">国奖级数学建模竞赛自动化系统</p>
			<p class="hero-desc">
				多智能体协作，从问题拆解到论文撰写全流程自动化，生成达到国奖水平的竞赛论文
			</p>
		</div>

		<div class="card">
			<h2 class="card-title">开始建模</h2>

			<div class="form-group">
				<label>竞赛类型</label>
				<div class="template-grid">
					<button
						v-for="tpl in templates"
						:key="tpl.value"
						class="template-btn"
						:class="{ active: compTemplate === tpl.value }"
						@click="compTemplate = tpl.value"
					>
						{{ tpl.label }}
					</button>
				</div>
			</div>

			<div class="form-group">
				<label>输出格式</label>
				<div class="template-grid">
					<button
						class="template-btn"
						:class="{ active: formatOutput === 'Markdown' }"
						@click="formatOutput = 'Markdown'"
					>
						Markdown
					</button>
					<button
						class="template-btn"
						:class="{ active: formatOutput === 'LaTeX' }"
						@click="formatOutput = 'LaTeX'"
					>
						LaTeX
					</button>
				</div>
			</div>

			<div class="form-group">
				<label>题目内容</label>
				<textarea
					v-model="quesAll"
					class="ques-input"
					rows="12"
					placeholder="请粘贴完整的数学建模题目..."
				></textarea>
			</div>

			<div class="form-group">
				<label>数据文件（可选）</label>
				<div class="file-upload">
					<input
						ref="fileInput"
						type="file"
						multiple
						@change="handleFileSelect"
						class="file-input"
					/>
					<div class="file-list" v-if="files.length > 0">
						<div v-for="(f, i) in files" :key="i" class="file-item">
							📄 {{ f.name }} ({{ (f.size / 1024).toFixed(1) }} KB)
						</div>
					</div>
				</div>
			</div>

			<div v-if="error" class="error-msg">{{ error }}</div>

			<button class="start-btn" :disabled="loading" @click="startModeling">
				{{ loading ? "启动中..." : "🚀 开始建模" }}
			</button>
		</div>
	</div>
</template>

<style scoped>
.home-page {
	max-width: 900px;
	margin: 0 auto;
}

.hero {
	text-align: center;
	padding: 48px 0 32px;
}

.hero h1 {
	font-size: 48px;
	font-weight: 800;
	color: var(--primary);
	margin-bottom: 8px;
}

.hero-sub {
	font-size: 18px;
	color: var(--text);
	margin-bottom: 8px;
}

.hero-desc {
	font-size: 14px;
	color: var(--text-secondary);
	max-width: 600px;
	margin: 0 auto;
	line-height: 1.6;
}

.card {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 32px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-title {
	font-size: 20px;
	font-weight: 600;
	margin-bottom: 24px;
}

.form-group {
	margin-bottom: 24px;
}

.form-group label {
	display: block;
	font-size: 14px;
	font-weight: 500;
	margin-bottom: 8px;
}

.template-grid {
	display: flex;
	gap: 12px;
	flex-wrap: wrap;
}

.template-btn {
	padding: 10px 20px;
	border: 1px solid var(--border);
	border-radius: 8px;
	background: white;
	cursor: pointer;
	font-size: 14px;
	transition: all 0.2s;
}

.template-btn:hover {
	border-color: var(--primary);
}

.template-btn.active {
	background: var(--primary);
	color: white;
	border-color: var(--primary);
}

.ques-input {
	width: 100%;
	border: 1px solid var(--border);
	border-radius: 8px;
	padding: 12px;
	font-size: 14px;
	font-family: inherit;
	resize: vertical;
	line-height: 1.6;
}

.ques-input:focus {
	outline: none;
	border-color: var(--primary);
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.file-input {
	border: 1px dashed var(--border);
	border-radius: 8px;
	padding: 16px;
	width: 100%;
	cursor: pointer;
}

.file-list {
	margin-top: 8px;
}

.file-item {
	font-size: 13px;
	color: var(--text-secondary);
	padding: 4px 0;
}

.error-msg {
	background: #fef2f2;
	color: var(--danger);
	padding: 12px;
	border-radius: 8px;
	margin-bottom: 16px;
	font-size: 14px;
}

.start-btn {
	width: 100%;
	padding: 14px;
	background: var(--primary);
	color: white;
	border: none;
	border-radius: 8px;
	font-size: 16px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
}

.start-btn:hover:not(:disabled) {
	background: var(--primary-dark);
}

.start-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}
</style>
