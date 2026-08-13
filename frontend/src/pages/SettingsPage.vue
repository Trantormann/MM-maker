<script setup lang="ts">
import { ref } from "vue";
import { modelingApi } from "../apis/modelingApi";
import { useSettingsStore } from "../stores/settings";

const settingsStore = useSettingsStore();
const saving = ref(false);
const message = ref("");
const error = ref("");

const agentLabels = [
	{ key: "coordinator", label: "协调者 (Coordinator)" },
	{ key: "modeler", label: "建模手 (Modeler)" },
	{ key: "coder", label: "代码手 (Coder)" },
	{ key: "writer", label: "写作手 (Writer)" },
	{ key: "reviewer", label: "评审手 (Reviewer)" },
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
}
</script>

<template>
	<div class="settings-page">
		<div class="card">
			<h2 class="page-title">API 配置</h2>
			<p class="page-desc">
				为每个智能体配置独立的 LLM 模型，不同的智能体可以使用不同的模型以获得最佳效果
			</p>

			<div v-for="agent in agentLabels" :key="agent.key" class="agent-config">
				<h3 class="agent-title">{{ agent.label }}</h3>
				<div class="config-grid">
					<div class="form-group">
						<label>API 类型</label>
						<select
							v-model="getConfigItem(agent.key).apiType"
							class="form-input"
						>
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
						<button class="validate-btn" @click="validateKey(agent.key)">
							验证
						</button>
					</div>
				</div>
			</div>

			<div class="agent-config">
				<h3 class="agent-title">OpenAlex 文献检索</h3>
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

			<div v-if="message" class="success-msg">{{ message }}</div>
			<div v-if="error" class="error-msg">{{ error }}</div>

			<button class="save-btn" :disabled="saving" @click="saveConfig">
				{{ saving ? "保存中..." : "保存配置" }}
			</button>
		</div>
	</div>
</template>

<style scoped>
.settings-page {
	max-width: 1000px;
	margin: 0 auto;
}

.card {
	background: var(--bg-card);
	border-radius: var(--radius);
	padding: 32px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.page-title {
	font-size: 24px;
	font-weight: 700;
	margin-bottom: 8px;
}

.page-desc {
	font-size: 14px;
	color: var(--text-secondary);
	margin-bottom: 32px;
}

.agent-config {
	border: 1px solid var(--border);
	border-radius: 8px;
	padding: 20px;
	margin-bottom: 20px;
}

.agent-title {
	font-size: 15px;
	font-weight: 600;
	margin-bottom: 16px;
	color: var(--primary);
}

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
	color: var(--text-secondary);
	margin-bottom: 6px;
}

.form-input {
	padding: 8px 12px;
	border: 1px solid var(--border);
	border-radius: 6px;
	font-size: 13px;
}

.form-input:focus {
	outline: none;
	border-color: var(--primary);
	box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.validate-btn {
	padding: 8px 16px;
	background: var(--bg);
	border: 1px solid var(--border);
	border-radius: 6px;
	cursor: pointer;
	font-size: 13px;
}

.validate-btn:hover {
	background: var(--border);
}

.success-msg {
	background: #f0fdf4;
	color: var(--success);
	padding: 12px;
	border-radius: 8px;
	margin-bottom: 16px;
}

.error-msg {
	background: #fef2f2;
	color: var(--danger);
	padding: 12px;
	border-radius: 8px;
	margin-bottom: 16px;
}

.save-btn {
	width: 100%;
	padding: 14px;
	background: var(--primary);
	color: white;
	border: none;
	border-radius: 8px;
	font-size: 15px;
	font-weight: 600;
	cursor: pointer;
}

.save-btn:hover:not(:disabled) {
	background: var(--primary-dark);
}

.save-btn:disabled {
	opacity: 0.6;
}
</style>
