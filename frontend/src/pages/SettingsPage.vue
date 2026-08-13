<script setup lang="ts">
import { ref } from "vue";
import { modelingApi } from "../apis/modelingApi";
import { useSettingsStore } from "../stores/settings";

const settingsStore = useSettingsStore();
const saving = ref(false);
const message = ref("");
const error = ref("");
const validating = ref("");

const agentLabels = [
	{ key: "coordinator", label: "协调者", role: "Coordinator", icon: "🧭", desc: "拆解问题，规划任务" },
	{ key: "modeler", label: "建模手", role: "Modeler", icon: "📐", desc: "建立数学模型" },
	{ key: "coder", label: "代码手", role: "Coder", icon: "💻", desc: "编写求解代码" },
	{ key: "writer", label: "写作手", role: "Writer", icon: "✍️", desc: "撰写竞赛论文" },
	{ key: "reviewer", label: "评审手", role: "Reviewer", icon: "🔍", desc: "审查与优化结果" },
];

// ---- Methods ----
function getConfigItem(key: string) {
	return (settingsStore as any)[key];
}

async function saveConfig() {
	saving.value = true;
	error.value = "";
	message.value = "";

	try {
		await modelingApi.saveApiConfig({
			coordinator: settingsStore.coordinator,
			modeler: settingsStore.modeler,
			coder: settingsStore.coder,
			writer: settingsStore.writer,
			reviewer: settingsStore.reviewer,
			openalex_email: settingsStore.openalexEmail,
		});
		message.value = "配置保存成功";
	} catch (e: any) {
		error.value = e.message || "保存失败";
	} finally {
		saving.value = false;
	}
}

async function validateKey(key: string) {
	const config = getConfigItem(key);
	if (!config.apiKey) {
		error.value = `${key} API Key 不能为空`;
		return;
	}
	validating.value = key;
	error.value = "";
	message.value = "";
	try {
		const result = await modelingApi.validateApiKey({
			apiKey: config.apiKey,
			baseUrl: config.baseUrl,
			modelId: config.modelId,
			apiType: config.apiType,
		});
		if (result.valid) {
			message.value = `${key} API Key 验证成功`;
		} else {
			error.value = `${key} 验证失败: ${result.message}`;
		}
	} catch (e: any) {
		error.value = `${key} 验证失败: ${e.message || "网络错误"}`;
	} finally {
		validating.value = "";
	}
}
</script>

<template>
	<div class="settings-page">
		<!-- Hero -->
		<div class="hero">
			<div class="hero-badge">⚙️ 模型配置</div>
			<h1>API 配置</h1>
			<p class="hero-desc">
				为每个智能体配置独立的 LLM 模型，不同智能体可选用不同模型以获得最佳效果
			</p>
		</div>

		<!-- 智能体配置 -->
		<div
			v-for="agent in agentLabels"
			:key="agent.key"
			class="card agent-card"
		>
			<div class="agent-header">
				<span class="agent-icon">{{ agent.icon }}</span>
				<div class="agent-meta">
					<h3 class="agent-title">{{ agent.label }}</h3>
					<span class="agent-role">{{ agent.role }}</span>
				</div>
				<span class="agent-desc">{{ agent.desc }}</span>
			</div>

			<div class="config-grid">
				<div class="form-group">
					<label>API 类型</label>
					<select v-model="getConfigItem(agent.key).apiType" class="form-input">
						<option value="openai-chat">OpenAI Chat</option>
						<option value="openai-responses">OpenAI Responses</option>
						<option value="anthropic">Anthropic</option>
					</select>
				</div>
				<div class="form-group">
					<label>模型 ID</label>
					<input
						v-model="getConfigItem(agent.key).modelId"
						class="form-input"
						placeholder="如 gpt-4o"
					/>
				</div>
				<div class="form-group">
					<label>API Key</label>
					<input
						v-model="getConfigItem(agent.key).apiKey"
						class="form-input"
						type="password"
						placeholder="sk-..."
					/>
				</div>
				<div class="form-group">
					<label>Base URL</label>
					<input
						v-model="getConfigItem(agent.key).baseUrl"
						class="form-input"
						placeholder="https://api.openai.com/v1"
					/>
				</div>
				<div class="form-group">
					<label>上下文窗口</label>
					<input
						v-model.number="getConfigItem(agent.key).contextWindow"
						class="form-input"
						type="number"
					/>
				</div>
				<div class="form-group">
					<label>&nbsp;</label>
					<button
						class="validate-btn"
						:disabled="validating === agent.key"
						@click="validateKey(agent.key)"
					>
						<span v-if="validating === agent.key" class="btn-spinner"></span>
						{{ validating === agent.key ? "验证中" : "验证" }}
					</button>
				</div>
			</div>
		</div>

		<!-- OpenAlex -->
		<div class="card agent-card">
			<div class="agent-header">
				<span class="agent-icon">📚</span>
				<div class="agent-meta">
					<h3 class="agent-title">OpenAlex 文献检索</h3>
					<span class="agent-role">Scholar</span>
				</div>
				<span class="agent-desc">检索相关学术文献与数据</span>
			</div>
			<div class="config-grid">
				<div class="form-group">
					<label>邮箱（用于文献检索）</label>
					<input
						v-model="settingsStore.openalexEmail"
						class="form-input"
						placeholder="your@email.com"
					/>
				</div>
			</div>
		</div>

		<!-- 提示 -->
		<div v-if="message" class="success-msg">
			<span>✓</span> {{ message }}
		</div>
		<div v-if="error" class="error-msg">
			<span>⚠️</span> {{ error }}
		</div>

		<!-- 保存 -->
		<button class="save-btn" :disabled="saving" @click="saveConfig">
			<span v-if="saving" class="btn-spinner"></span>
			{{ saving ? "保存中..." : "💾 保存配置" }}
		</button>
	</div>
</template>

<style scoped>
.settings-page {
	max-width: 920px;
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
	font-size: 32px;
	font-weight: 800;
	background: linear-gradient(135deg, var(--primary), var(--primary-light));
	-webkit-background-clip: text;
	-webkit-text-fill-color: transparent;
	background-clip: text;
	margin-bottom: 8px;
}

.hero-desc {
	font-size: 14px;
	color: var(--text-secondary);
	line-height: 1.6;
}

/* ---- Card ---- */
.card {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 24px;
	box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.agent-card {
	margin-bottom: 16px;
}

.agent-header {
	display: flex;
	align-items: center;
	gap: 12px;
	padding-bottom: 16px;
	margin-bottom: 18px;
	border-bottom: 1px solid var(--border);
}

.agent-icon {
	width: 40px;
	height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: rgba(37, 99, 235, 0.08);
	border-radius: 10px;
	font-size: 20px;
	flex-shrink: 0;
}

.agent-meta {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.agent-title {
	font-size: 16px;
	font-weight: 700;
	color: var(--text);
}

.agent-role {
	font-size: 12px;
	color: var(--primary);
	font-weight: 500;
}

.agent-desc {
	margin-left: auto;
	font-size: 12px;
	color: var(--text-secondary);
	text-align: right;
}

/* ---- 表单 ---- */
.config-grid {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 16px;
}

.form-group {
	display: flex;
	flex-direction: column;
}

.form-group label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-secondary);
	margin-bottom: 6px;
}

.form-input {
	padding: 10px 12px;
	border: 1.5px solid var(--border);
	border-radius: 8px;
	font-size: 13px;
	font-family: inherit;
	background: white;
	transition: border-color 0.2s, box-shadow 0.2s;
}

.form-input:focus {
	outline: none;
	border-color: var(--primary);
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.validate-btn {
	padding: 10px 16px;
	background: var(--bg);
	border: 1.5px solid var(--border);
	border-radius: 8px;
	cursor: pointer;
	font-size: 13px;
	font-weight: 500;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	transition: all 0.2s;
}

.validate-btn:hover:not(:disabled) {
	background: var(--primary);
	border-color: var(--primary);
	color: white;
}

.validate-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

/* ---- 提示 ---- */
.success-msg {
	display: flex;
	align-items: center;
	gap: 8px;
	background: #f0fdf4;
	color: #16a34a;
	padding: 12px 16px;
	border-radius: 10px;
	margin-bottom: 16px;
	font-size: 14px;
}

.error-msg {
	display: flex;
	align-items: center;
	gap: 8px;
	background: #fef2f2;
	color: var(--danger);
	padding: 12px 16px;
	border-radius: 10px;
	margin-bottom: 16px;
	font-size: 14px;
}

/* ---- 保存 ---- */
.save-btn {
	width: 100%;
	padding: 14px;
	background: linear-gradient(135deg, var(--primary), var(--primary-light));
	color: white;
	border: none;
	border-radius: 10px;
	font-size: 15px;
	font-weight: 600;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	transition: all 0.2s;
	box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
}

.save-btn:hover:not(:disabled) {
	transform: translateY(-1px);
	box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
}

.save-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

/* ---- 加载动画 ---- */
.btn-spinner {
	width: 14px;
	height: 14px;
	border: 2px solid rgba(255, 255, 255, 0.4);
	border-top-color: white;
	border-radius: 50%;
	animation: spin 0.6s linear infinite;
}

@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}

/* ---- 响应式 ---- */
@media (max-width: 768px) {
	.config-grid {
		grid-template-columns: 1fr;
	}
	.agent-desc {
		display: none;
	}
}
</style>
