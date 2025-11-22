const API_BASE = '/admin_api/workflow-orchestrator';

const elements = {
    workflowList: document.getElementById('workflows-list'),
    workflowSearch: document.getElementById('workflow-search'),
    createWorkflowBtn: document.getElementById('create-workflow-btn'),
    commanderSelect: document.getElementById('commander-select'),
    participantsGrid: document.getElementById('participants-grid'),
    workflowId: document.getElementById('workflow-id'),
    commonPrompt: document.getElementById('common-prompt'),
    stagesText: document.getElementById('stages-text'),
    statusText: document.getElementById('status-text'),
    reloadButton: document.getElementById('reload-button'),
    saveButtonTop: document.getElementById('save-button'),
    saveButtonBottom: document.getElementById('save-button-bottom'),
    deleteButton: document.getElementById('delete-button'),
    refreshWorkflowsButton: document.getElementById('refresh-workflows-button'),
    workflowsRaw: document.getElementById('workflows-raw'),
};

let agents = [];
let workflows = [];
let selectedWorkflowName = null;
let initFallbackTimer = null;

// 内置示例数据（接口不可用或返回空时兜底）
const FALLBACK_AGENTS = [
    { id: 'planner', agent_name: '策略规划官' },
    { id: 'executor', agent_name: '执行专员' },
    { id: 'reviewer', agent_name: '质检审核' },
    { id: 'summarizer', agent_name: '总结输出' },
];

const FALLBACK_WORKFLOWS = [
    {
        name: 'GenericTaskFlow',
        commander_agent_name: '策略规划官',
        participants: ['planner', 'executor', 'reviewer', 'summarizer'],
        common_prompt: '你正在参与一个多 Agent 工作流，请严格按步骤执行并简要回复，必要时总结关键信息以便后续步骤引用。',
        stages_text: [
            '阶段1：优化用户需求描述',
            '阶段2：拆解可执行任务清单',
            '阶段3：执行并输出结果',
            '阶段4：复核并给出总结',
        ].join('\n'),
        steps: [
            { id: 'S1_optimize_prompt', role: 'planner', input_template: '优化用户任务描述：{{user_task}}', outputs: ['optimized_prompt'] },
            { id: 'S2_plan', role: 'planner', depend_on: ['S1_optimize_prompt'], input_template: '基于 {{S1_optimize_prompt.optimized_prompt}} 拆解任务', outputs: ['plan'] },
            { id: 'S3_execute', role: 'executor', depend_on: ['S2_plan'], input_template: '根据计划执行：{{S2_plan.plan}}', outputs: ['execution_result'] },
            { id: 'S4_review', role: 'reviewer', depend_on: ['S3_execute'], input_template: '审核执行结果：{{S3_execute.execution_result}}', outputs: ['review_notes'] },
            { id: 'S5_summary', role: 'summarizer', depend_on: ['S3_execute', 'S4_review'], input_template: '总结并给出后续建议', outputs: ['final_report'] },
        ],
    },
];

function setStatus(message, type = 'info') {
    if (!elements.statusText) return;
    elements.statusText.textContent = message;
    elements.statusText.style.color = type === 'error' ? '#ef4444' : '#94a3b8';
}

async function fetchJSON(url, options = {}, timeoutMs = 6000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, signal: controller.signal, ...options });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status} - ${text}`);
        }
        const text = await res.text();
        try {
            return JSON.parse(text);
        } catch (err) {
            throw new Error(`解析返回结果失败: ${err.message} | 原始: ${text.slice(0, 200)}`);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            throw new Error(`请求超时 (${timeoutMs}ms): ${url}`);
        }
        throw err;
    } finally {
        clearTimeout(timer);
    }
}

function normalizeWorkflows(data) {
    const payload =
        data?.workflows ||
        data?.data?.workflows ||
        (data?.data && !Array.isArray(data.data) ? data.data : null) ||
        data?.result ||
        data;

    if (!payload) return [];
    if (Array.isArray(payload)) return payload;

    if (payload.workflows && typeof payload.workflows === 'object') {
        return Object.entries(payload.workflows).map(([name, payloadItem]) => ({
            name,
            ...payloadItem,
        }));
    }

    if (typeof payload === 'object') {
        return Object.entries(payload)
            .map(([name, payloadItem]) => ({ name, ...payloadItem }))
            .filter(item => item.steps || item.participants || item.common_prompt || item.stages_text);
    }
    return [];
}

function renderWorkflowsRaw(data) {
    if (elements.workflowsRaw) {
        try {
            elements.workflowsRaw.textContent = JSON.stringify(data, null, 2);
        } catch {
            elements.workflowsRaw.textContent = '无法解析工作流数据';
        }
    }
}

function renderWorkflowsList() {
    const list = elements.workflowList;
    if (!list) return;
    list.innerHTML = '';

    const keyword = elements.workflowSearch?.value?.trim().toLowerCase() || '';
    const filtered = workflows.filter(w => (w.name || '').toLowerCase().includes(keyword));

    if (filtered.length === 0) {
        list.innerHTML = '<div class="placeholder">没有匹配的工作流</div>';
        return;
    }

    filtered.forEach(wf => {
        const card = document.createElement('div');
        card.className = 'workflow-card' + (wf.name === selectedWorkflowName ? ' active' : '');
        card.dataset.name = wf.name || '';

        const stepsCount = Array.isArray(wf.steps) ? wf.steps.length : (wf.steps_count || wf.stepsCount || 0);
        const participantCount = Array.isArray(wf.participants) ? wf.participants.length : (wf.participant_agents?.length || wf.participantAgents?.length || 0);

        card.innerHTML = `
            <div class="workflow-name">${wf.name || '未命名'}</div>
            <div class="workflow-meta">${stepsCount || 0} Steps · ${participantCount || 0} Agents</div>
        `;
        card.addEventListener('click', () => selectWorkflow(wf.name));
        list.appendChild(card);
    });
}

function renderAgents(participantNames = []) {
    if (!elements.participantsGrid) return;
    elements.participantsGrid.innerHTML = '';

    if (agents.length === 0) {
        elements.participantsGrid.innerHTML = '<div class="placeholder">未加载到 Agent，请检查 AgentAssistant 配置</div>';
        return;
    }

    agents.forEach(agent => {
        const name = agent.agent_name || agent.name || agent.chinese_name || agent;
        const roleId = agent.id || agent.alias || name;
        const isChecked = participantNames.includes(name) || participantNames.includes(roleId);

        const label = document.createElement('label');
        label.className = 'agent-card' + (isChecked ? ' active' : '');

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = name;
        checkbox.checked = isChecked;
        checkbox.addEventListener('change', () => {
            label.classList.toggle('active', checkbox.checked);
        });

        const info = document.createElement('div');
        info.className = 'agent-info';
        const title = document.createElement('span');
        title.className = 'agent-name';
        title.textContent = name;
        const meta = document.createElement('span');
        meta.className = 'agent-meta';
        meta.textContent = `ID: ${roleId}`;
        info.appendChild(title);
        info.appendChild(meta);

        label.appendChild(checkbox);
        label.appendChild(info);
        elements.participantsGrid.appendChild(label);
    });
}

function applyFallback(reason) {
    console.warn('[WorkflowOrchestrator] 使用内置示例，原因：', reason);
    agents = FALLBACK_AGENTS;
    workflows = FALLBACK_WORKFLOWS;

    if (elements.commanderSelect) {
        elements.commanderSelect.innerHTML = '';
        agents.forEach(agent => {
            const name = agent.agent_name || agent.name || agent.chinese_name || agent;
            const option = document.createElement('option');
            option.value = name;
            option.textContent = name;
            elements.commanderSelect.appendChild(option);
        });
    }

    renderAgents(workflows[0]?.participants || []);
    renderWorkflowsRaw({ fallback: true, reason, workflows: workflows.map(w => w.name) });
    renderWorkflowsList();
    selectWorkflow(workflows[0]?.name || null);
    setStatus(`接口异常，已加载内置示例 (${reason})`, 'error');
}

function seedWithFallback(message = '加载中，先展示示例') {
    agents = FALLBACK_AGENTS;
    workflows = FALLBACK_WORKFLOWS;
    renderWorkflowsList();
    renderAgents(workflows[0]?.participants || []);
    renderWorkflowsRaw({ fallbackPreview: true, workflows: workflows.map(w => w.name) });
    selectWorkflow(workflows[0]?.name || null);
    setStatus(message);
}

function collectParticipants() {
    const checkboxes = elements.participantsGrid?.querySelectorAll('input[type="checkbox"]') || [];
    return Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
}

function fillFormFromWorkflow(name) {
    const wf = workflows.find(w => w.name === name);
    selectedWorkflowName = name || null;
    if (!wf) {
        elements.workflowId.value = name || '';
        elements.commonPrompt.value = '';
        elements.stagesText.value = '';
        renderAgents([]);
        renderWorkflowsList();
        return;
    }

    elements.workflowId.value = wf.name || '';
    elements.commonPrompt.value = wf.common_prompt || wf.commonPrompt || '';
    elements.stagesText.value =
        wf.stages_text ||
        wf.stagesText ||
        (Array.isArray(wf.steps) ? wf.steps.map(s => s.input_template || s.inputTemplate || s.input || '').join('\n') : '');

    const commander = wf.commander_agent || wf.commander_agent_name || wf.commander || '';
    if (elements.commanderSelect) {
        elements.commanderSelect.value = commander;
    }

    const participants = wf.participant_agents || wf.participantAgents || wf.participants || [];
    renderAgents(participants);
    renderWorkflowsList();
}

function selectWorkflow(name) {
    fillFormFromWorkflow(name);
    setStatus(`已选中：${name || '新建'}`);
}

async function loadAgents() {
    setStatus('加载 Agent 列表...');
    try {
        const data = await fetchJSON(`${API_BASE}/agents`);
        const agentPayload = data?.data || data?.result || data?.agents || [];
        agents = Array.isArray(agentPayload) ? agentPayload : agentPayload.agents || [];
        renderAgents();

        if (elements.commanderSelect) {
            elements.commanderSelect.innerHTML = '';
            agents.forEach(agent => {
                const name = agent.agent_name || agent.name || agent.chinese_name || agent;
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                elements.commanderSelect.appendChild(option);
            });
        }
        setStatus('Agent 列表已加载');
    } catch (e) {
        console.error('[WorkflowOrchestrator] 加载 Agents 失败:', e);
        if (elements.participantsGrid) {
            elements.participantsGrid.innerHTML = `<div class="placeholder">Agent 列表加载失败：${e.message}</div>`;
        }
        applyFallback(`Agent 加载失败: ${e.message}`);
    }
}

async function loadWorkflows() {
    setStatus('加载工作流...');
    try {
        const data = await fetchJSON(`${API_BASE}/workflows`);
        workflows = normalizeWorkflows(data);
        renderWorkflowsRaw(data);
        renderWorkflowsList();
        if (workflows.length === 0) {
            applyFallback('未返回任何工作流');
        } else {
            selectWorkflow(workflows[0].name);
            setStatus('工作流列表已刷新');
        }
    } catch (e) {
        console.error('[WorkflowOrchestrator] 加载工作流失败:', e);
        renderWorkflowsRaw({ error: e.message });
        if (elements.workflowsList) {
            elements.workflowsList.innerHTML = `<div class="placeholder">加载工作流失败：${e.message}</div>`;
        }
        applyFallback(`工作流加载失败: ${e.message}`);
    }
}

async function saveWorkflow() {
    const workflowName = elements.workflowId.value.trim();
    const commander = elements.commanderSelect.value;
    const participants = collectParticipants();
    const stagesText = elements.stagesText.value;
    const commonPrompt = elements.commonPrompt.value;

    if (!workflowName) {
        setStatus('请填写工作流名称', 'error');
        return;
    }
    if (!commander) {
        setStatus('请选择总指挥 Agent', 'error');
        return;
    }

    setStatus('正在保存工作流...');
    try {
        const body = {
            workflow_name: workflowName,
            commander_agent: commander,
            participant_agents: participants,
            stages_text: stagesText,
            common_prompt: commonPrompt,
        };
        const res = await fetchJSON(`${API_BASE}/configure`, {
            method: 'POST',
            body: JSON.stringify(body),
        });
        setStatus(res?.result || res?.message || '保存成功');
        await loadWorkflows();
        selectWorkflow(workflowName);
    } catch (e) {
        console.error('[WorkflowOrchestrator] 保存失败:', e);
        setStatus(`保存失败: ${e.message}`, 'error');
    }
}

async function reloadWorkflows() {
    setStatus('重新加载工作流配置...');
    try {
        await fetchJSON(`${API_BASE}/reload`, { method: 'POST' });
        await loadWorkflows();
        setStatus('已重新加载');
    } catch (e) {
        console.error('[WorkflowOrchestrator] 重载失败:', e);
        applyFallback(`重载失败: ${e.message}`);
    }
}

function deleteWorkflow() {
    const name = elements.workflowId.value.trim();
    if (!name) {
        setStatus('当前没有可删除的工作流', 'error');
        return;
    }
    elements.workflowId.value = '';
    elements.commonPrompt.value = '';
    elements.stagesText.value = '';
    renderAgents([]);
    selectedWorkflowName = null;
    setStatus(`已清空表单：${name}`);
}

function bindEvents() {
    elements.createWorkflowBtn?.addEventListener('click', () => {
        selectedWorkflowName = null;
        elements.workflowId.value = '';
        elements.commonPrompt.value = '';
        elements.stagesText.value = '';
        renderAgents([]);
        renderWorkflowsList();
        setStatus('新建工作流');
    });

    elements.workflowSearch?.addEventListener('input', renderWorkflowsList);
    elements.saveButtonTop?.addEventListener('click', saveWorkflow);
    elements.saveButtonBottom?.addEventListener('click', saveWorkflow);
    elements.reloadButton?.addEventListener('click', reloadWorkflows);
    elements.refreshWorkflowsButton?.addEventListener('click', loadWorkflows);
    elements.deleteButton?.addEventListener('click', deleteWorkflow);
}

async function init() {
    bindEvents();
    // 先用示例填充，防止首屏空白
    seedWithFallback('加载中，先展示示例');
    // 8s 兜底：若接口无响应则用示例
    initFallbackTimer = setTimeout(() => {
        if (agents.length === 0 || workflows.length === 0) {
            applyFallback('初始化超时，使用示例数据');
        }
    }, 8000);

    await loadAgents();
    await loadWorkflows();

    if (initFallbackTimer) {
        clearTimeout(initFallbackTimer);
        initFallbackTimer = null;
    }
}

init().catch(err => {
    console.error('[WorkflowOrchestrator] 初始化失败:', err);
    setStatus(`初始化失败: ${err.message}`, 'error');
    applyFallback(err.message);
});
