const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

let WORKFLOW_MAX_RETRIES_PER_STEP = 3;
let WORKFLOW_DEBUG_MODE = false;
let WORKFLOW_DEFAULT_LOG_FOLDER = 'WorkflowDebugLogs';
let workflowsConfig = { agents: [], workflows: {} };
let pushVcpInfo = () => {};
let PluginManagerRef;
let aaAgents = {};
let aaAgentList = [];
const workflowInstances = new Map(); // instanceId -> { status, workflowName, steps, createdAt, finishedAt, error, results }
const RUNTIME_STATE_DIR = path.join(__dirname, 'runtime_state');
const { buildWorkflow } = require('./workflow_config_builder');

function initialize(config, dependencies) {
  loadLocalConfigEnv();
  WORKFLOW_MAX_RETRIES_PER_STEP = getFirstDefined(config.WORKFLOW_MAX_RETRIES_PER_STEP, WORKFLOW_MAX_RETRIES_PER_STEP);
  WORKFLOW_DEBUG_MODE = getFirstDefined(config.WORKFLOW_DEBUG_MODE, WORKFLOW_DEBUG_MODE);
  WORKFLOW_DEFAULT_LOG_FOLDER = getFirstDefined(config.WORKFLOW_DEFAULT_LOG_FOLDER, WORKFLOW_DEFAULT_LOG_FOLDER);

  if (dependencies) {
    if (dependencies.vcpLogFunctions && typeof dependencies.vcpLogFunctions.pushVcpInfo === 'function') {
      pushVcpInfo = dependencies.vcpLogFunctions.pushVcpInfo;
    }
    if (dependencies.PluginManager) {
      PluginManagerRef = dependencies.PluginManager;
    }
  }

  loadWorkflows();
  loadAAAgents();
  loadPersistedInstances();
  console.log('[WorkflowOrchestrator] Initialized.');
}

function getFirstDefined(value, fallback) {
  return value !== undefined && value !== null ? value : fallback;
}

function loadLocalConfigEnv() {
  const envPath = path.join(__dirname, 'config.env');
  if (!fs.existsSync(envPath)) return;
  try {
    const dotenv = require('dotenv');
    const parsed = dotenv.parse(fs.readFileSync(envPath, 'utf8'));
    if (parsed.WORKFLOW_MAX_RETRIES_PER_STEP) {
      WORKFLOW_MAX_RETRIES_PER_STEP = parseInt(parsed.WORKFLOW_MAX_RETRIES_PER_STEP, 10) || WORKFLOW_MAX_RETRIES_PER_STEP;
    }
    if (parsed.WORKFLOW_DEBUG_MODE !== undefined) {
      WORKFLOW_DEBUG_MODE = String(parsed.WORKFLOW_DEBUG_MODE).toLowerCase() === 'true';
    }
    if (parsed.WORKFLOW_DEFAULT_LOG_FOLDER) {
      WORKFLOW_DEFAULT_LOG_FOLDER = parsed.WORKFLOW_DEFAULT_LOG_FOLDER;
    }
  } catch (err) {
    console.error('[WorkflowOrchestrator] Failed to load config.env:', err.message);
  }
}

function loadWorkflows() {
  const workflowsPath = path.join(__dirname, 'workflows.json');
  try {
    if (fs.existsSync(workflowsPath)) {
      const content = fs.readFileSync(workflowsPath, 'utf8');
      workflowsConfig = JSON.parse(content);
      console.log(`[WorkflowOrchestrator] Loaded ${Object.keys(workflowsConfig.workflows || {}).length} workflows.`);
    } else {
      console.warn('[WorkflowOrchestrator] workflows.json not found.');
      workflowsConfig = { agents: [], workflows: {} };
    }
  } catch (error) {
    console.error('[WorkflowOrchestrator] Error loading workflows.json:', error);
    workflowsConfig = { agents: [], workflows: {} };
  }
}

function saveWorkflows() {
  try {
    const workflowsPath = path.join(__dirname, 'workflows.json');
    fs.writeFileSync(workflowsPath, JSON.stringify(workflowsConfig, null, 2), 'utf8');
  } catch (err) {
    console.error('[WorkflowOrchestrator] Failed to save workflows.json:', err.message);
  }
}

function loadAAAgents() {
  try {
    const aaEnvPath = path.join(__dirname, '..', 'AgentAssistant', 'config.env');
    if (!fs.existsSync(aaEnvPath)) return;
    const dotenv = require('dotenv');
    const parsed = dotenv.parse(fs.readFileSync(aaEnvPath, 'utf8'));
    const temp = {};
    const list = [];
    for (const key of Object.keys(parsed)) {
      const match = key.match(/^AGENT_([A-Z0-9_]+)_CHINESE_NAME$/i);
      if (match) {
        const base = match[1];
        const name = parsed[key];
        const modelId = parsed[`AGENT_${base}_MODEL_ID`];
        const systemPrompt = parsed[`AGENT_${base}_SYSTEM_PROMPT`];
        temp[name] = { modelId, systemPrompt };
        list.push({ name, base, modelId, systemPrompt });
      }
    }
    aaAgents = temp;
    aaAgentList = list;
    if (WORKFLOW_DEBUG_MODE) {
      console.log(`[WorkflowOrchestrator] Loaded ${Object.keys(aaAgents).length} AA agents`);
    }
  } catch (err) {
    console.error('[WorkflowOrchestrator] Failed to load AgentAssistant config:', err.message);
  }
}

function loadPersistedInstances() {
  try {
    if (!fs.existsSync(RUNTIME_STATE_DIR)) return;
    const files = fs.readdirSync(RUNTIME_STATE_DIR).filter(f => f.endsWith('.json'));
    for (const file of files) {
      const p = path.join(RUNTIME_STATE_DIR, file);
      const raw = JSON.parse(fs.readFileSync(p, 'utf8'));
      workflowInstances.set(raw.workflowInstanceId, raw);
    }
  } catch (err) {
    console.error('[WorkflowOrchestrator] Failed to load persisted instances:', err.message);
  }
}

function persistInstance(instanceId) {
  try {
    fs.mkdirSync(RUNTIME_STATE_DIR, { recursive: true });
    const filePath = path.join(RUNTIME_STATE_DIR, `${instanceId}.json`);
    const inst = workflowInstances.get(instanceId);
    if (inst) {
      fs.writeFileSync(filePath, JSON.stringify({ workflowInstanceId: instanceId, ...inst }, null, 2), 'utf8');
    }
  } catch (err) {
    if (WORKFLOW_DEBUG_MODE) console.error('[WorkflowOrchestrator] Persist instance failed:', err.message);
  }
}

async function processToolCall(args) {
  const { command } = args;

  if (command === 'StartWorkflow') {
    const { workflow_name, user_task, session_id } = args;
    return await startWorkflow(workflow_name, user_task, session_id);
  }
  if (command === 'GetWorkflowStatus') {
    return getWorkflowStatus(args.workflowInstanceId);
  }
  if (command === 'ListWorkflows') {
    return { status: 'success', data: workflowsConfig };
  }
  if (command === 'ListAAAgents') {
    return { status: 'success', data: aaAgentList };
  }
  if (command === 'UpdateWorkflows') {
    try {
      const payload = typeof args.workflows_json === 'string' ? JSON.parse(args.workflows_json) : args.workflows_json;
      if (!payload || !payload.workflows) return { status: 'error', error: 'Invalid workflows payload' };
      const workflowsPath = path.join(__dirname, 'workflows.json');
      fs.writeFileSync(workflowsPath, JSON.stringify(payload, null, 2), 'utf8');
      loadWorkflows();
      return { status: 'success', result: 'Workflows updated and reloaded.' };
    } catch (err) {
      return { status: 'error', error: `Failed to update workflows: ${err.message}` };
    }
  }
  if (command === 'ReloadWorkflows') {
    loadWorkflows();
    return { status: 'success', result: 'Workflows reloaded.' };
  }
  if (command === 'ConfigureWorkflow') {
    try {
      return configureWorkflow(args);
    } catch (err) {
      return { status: 'error', error: err.message };
    }
  }
  return { status: 'error', error: `Unknown command: ${command}` };
}

async function startWorkflow(workflowName, userTask, sessionId) {
  if (!workflowsConfig.workflows[workflowName]) {
    return { status: 'error', error: `Workflow '${workflowName}' not found.` };
  }

  const workflowDef = workflowsConfig.workflows[workflowName];
  const instanceId = uuidv4();

  workflowInstances.set(instanceId, {
    workflowName,
    status: 'running',
    steps: {},
    createdAt: new Date().toISOString(),
    finishedAt: null,
    error: null,
    results: {}
  });
  persistInstance(instanceId);

  pushStatus({
    workflowInstanceId: instanceId,
    workflowName,
    status: 'started'
  });

  executeWorkflow(instanceId, workflowName, workflowDef, { user_task: userTask || '' }, sessionId).catch(err => {
    console.error(`[WorkflowOrchestrator] Workflow ${instanceId} failed:`, err);
  });

  return {
    status: 'success',
    result: `Workflow '${workflowName}' started. Instance ID: ${instanceId}`,
    workflowInstanceId: instanceId
  };
}

function getWorkflowStatus(instanceId) {
  if (!instanceId || !workflowInstances.has(instanceId)) {
    return { status: 'error', error: `Workflow instance '${instanceId}' not found.` };
  }
  return { status: 'success', data: workflowInstances.get(instanceId) };
}

async function executeWorkflow(instanceId, workflowName, workflowDef, initialContext, sessionId) {
  const context = { ...initialContext };
  const results = {};
  const commonPrompt = workflowDef.common_prompt || '';
  const steps = workflowDef.steps ? workflowDef.steps.map(s => ({ ...s })) : [];
  const retryPolicy = workflowDef.retry_policy || {};
  const remaining = [...steps];
  const completed = new Set();

  while (remaining.length > 0) {
    const ready = remaining.filter(s => !s.__running && (s.depend_on || []).every(d => completed.has(d)));
    if (ready.length === 0) {
      failInstance(instanceId, workflowName, 'No ready steps found (possible dependency cycle or unresolved dependencies).');
      await writeDebugLog(workflowName, instanceId, workflowDef, results, new Error('Dependency deadlock'));
      return;
    }

    const executions = ready.map(step =>
      runStep({
        step,
        instanceId,
        workflowName,
        commonPrompt,
        retryPolicy,
        context,
        results,
        remaining,
        sessionId
      })
        .then(() => ({ step, success: true }))
        .catch(error => ({ step, success: false, error }))
    );

    const outcomes = await Promise.all(executions);
    for (const outcome of outcomes) {
      remaining.splice(remaining.indexOf(outcome.step), 1);
      if (outcome.success) {
        completed.add(outcome.step.id);
      } else {
        failInstance(instanceId, workflowName, outcome.error ? outcome.error.message : 'Unknown error');
        await writeDebugLog(workflowName, instanceId, workflowDef, results, outcome.error);
        return;
      }
    }
  }

  completeInstance(instanceId, workflowName, results);
  await writeDebugLog(workflowName, instanceId, workflowDef, results, null);
}

async function runStep({ step, instanceId, workflowName, commonPrompt, retryPolicy, context, results, remaining, sessionId }) {
  const stepState = {
    status: 'running',
    attempts: 0,
    result: null,
    error: null
  };
  updateStepState(instanceId, step.id, stepState);
  pushStatus({
    workflowInstanceId: instanceId,
    workflowName,
    currentStepId: step.id,
    stepStatus: 'running',
    role: step.role,
    message: `Executing step ${step.id}...`
  });

  const maxRetries = retryPolicy.max_retries_per_step || WORKFLOW_MAX_RETRIES_PER_STEP;
  let correctionHint = '';
  let lastError = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    stepState.attempts = attempt;
    try {
      const prompt = renderTemplate(step.input_template || '', context, results);
      const fullPrompt = buildFullPrompt(commonPrompt, prompt, step, workflowName, instanceId, correctionHint);
      const agentName = getAgentNameForRole(step.role);
      if (!agentName) throw new Error(`No agent found for role ${step.role}`);

      const PM = PluginManagerRef || require('../../Plugin.js');
      // push waiting status before tool call
      pushStatus({
        workflowInstanceId: instanceId,
        workflowName,
        currentStepId: step.id,
        stepStatus: 'waiting_for_tool',
        message: `等待 Agent ${agentName} 执行 (step ${step.id})`
      });
      const result = await PM.processToolCall('AgentAssistant', {
        agent_name: agentName,
        prompt: fullPrompt,
        temporary_contact: true,
        session_id: sessionId || `workflow_${instanceId}`
      });

      if (result.status === 'error') {
        throw new Error(result.error || 'AgentAssistant returned error');
      }

      const outputNames = Array.isArray(step.outputs) && step.outputs.length > 0 ? step.outputs : ['output'];
      const stepResult = {};
      if (result && typeof result.result === 'object' && !Array.isArray(result.result)) {
        for (const name of outputNames) {
          stepResult[name] = result.result[name] || result.result;
        }
      } else {
        for (const name of outputNames) {
          stepResult[name] = result.result;
        }
      }
      results[step.id] = stepResult;
      context[`STEP_${step.id}`] = stepResult;

      stepState.status = 'success';
      stepState.result = stepResult;
      updateStepState(instanceId, step.id, stepState);
      pushStatus({
        workflowInstanceId: instanceId,
        workflowName,
        currentStepId: step.id,
        stepStatus: 'success',
        resultPreview: typeof result.result === 'string' ? `${result.result}`.substring(0, 100) + '...' : '[object]'
      });

      if (typeof result.result === 'string') {
        const overrides = parseOverrides(result.result);
        if (overrides.length > 0) {
          applyOverrides(overrides, remaining, step);
        }
      }
      return true;
    } catch (err) {
      lastError = err;
      stepState.error = err.message;
      stepState.status = attempt >= maxRetries ? 'failed' : 'retrying';
      updateStepState(instanceId, step.id, stepState);

      pushStatus({
        workflowInstanceId: instanceId,
        workflowName,
        currentStepId: step.id,
        stepStatus: stepState.status,
        message: `Step ${step.id} attempt ${attempt} failed: ${err.message}`
      });

      const fallbackAgentName = retryPolicy.fallback_agent || workflowsConfig.retry_policy?.fallback_agent;
      if (attempt < maxRetries && fallbackAgentName) {
        try {
          const PM = PluginManagerRef || require('../../Plugin.js');
          const fb = await PM.processToolCall('AgentAssistant', {
            agent_name: fallbackAgentName,
            prompt: `下面的步骤在执行时失败，请给出修正提示词或排查建议：\n步骤ID: ${step.id}\n角色: ${step.role}\n错误: ${err.message}\n当前任务: ${renderTemplate(step.input_template || '', context, results)}`,
            temporary_contact: true,
            session_id: sessionId || `workflow_${instanceId}_fallback`
          });
          if (fb && fb.status === 'success' && typeof fb.result === 'string') {
            correctionHint = `\n\n[调试提示] ${fb.result}`;
          }
        } catch (fbErr) {
          if (WORKFLOW_DEBUG_MODE) console.error('[WorkflowOrchestrator] Fallback agent failed:', fbErr.message);
        }
      }

      if (attempt >= maxRetries) {
        throw lastError || new Error(`Step ${step.id} failed`);
      }
    }
  }
  return true;
}

function renderTemplate(template, context, results) {
  let output = String(template || '');
  for (const [key, value] of Object.entries(context)) {
    output = output.replace(new RegExp(`{{${escapeRegex(key)}}}`, 'g'), String(value));
  }
  for (const [stepId, stepResult] of Object.entries(results)) {
    for (const [key, value] of Object.entries(stepResult)) {
      output = output.replace(new RegExp(`{{${escapeRegex(stepId)}\\.${escapeRegex(key)}}}`, 'g'), String(value));
    }
  }
  return output;
}

function buildFullPrompt(commonPrompt, prompt, step, workflowName, instanceId, correctionHint = '') {
  const parts = [];
  if (commonPrompt) parts.push(commonPrompt);
  parts.push(`[当前任务] ${prompt}${correctionHint ? correctionHint : ''}`);
  parts.push(`[上下文] 工作流: ${workflowName} | 实例: ${instanceId} | 步骤: ${step.id} | 角色: ${step.role}`);
  return parts.join('\n\n');
}

function escapeRegex(str) {
  return str.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
}

function getAgentNameForRole(role) {
  const agentDef = (workflowsConfig.agents || []).find(a => a.id === role);
  if (agentDef && agentDef.enabled !== false) return agentDef.agent_name;
  // commander override per workflow
  for (const wf of Object.values(workflowsConfig.workflows || {})) {
    if (wf.commander_agent_name && (role === 'commander' || role === wf.commander_role)) {
      return wf.commander_agent_name;
    }
    if (wf.role_map && wf.role_map[role]) {
      return wf.role_map[role];
    }
  }
  if (aaAgents[role]) return role; // role name is agent name
  return null;
}

function updateStepState(instanceId, stepId, state) {
  const inst = workflowInstances.get(instanceId);
  if (!inst) return;
  inst.steps[stepId] = { ...(inst.steps[stepId] || {}), ...state };
  persistInstance(instanceId);
}

function failInstance(instanceId, workflowName, message) {
  const inst = workflowInstances.get(instanceId);
  if (inst) {
    inst.status = 'failed';
    inst.error = message;
    inst.finishedAt = new Date().toISOString();
  }
  persistInstance(instanceId);
  pushStatus({
    workflowInstanceId: instanceId,
    workflowName,
    status: 'failed',
    message
  });
}

function completeInstance(instanceId, workflowName, results) {
  const inst = workflowInstances.get(instanceId);
  if (inst) {
    inst.status = 'completed';
    inst.results = results;
    inst.finishedAt = new Date().toISOString();
  }
  persistInstance(instanceId);
  pushStatus({
    workflowInstanceId: instanceId,
    workflowName,
    status: 'completed',
    results
  });
}

function pushStatus(payload) {
  pushVcpInfo({
    ...payload,
    timestamp: new Date().toISOString(),
    type: payload.type || 'WORKFLOW_STATUS'
  });
}

async function writeDebugLog(workflowName, instanceId, workflowDef, results, error) {
  try {
    const folder = workflowDef.log_options?.diary_folder || WORKFLOW_DEFAULT_LOG_FOLDER;
    const root = path.join(__dirname, '..', '..', 'dailynote', folder);
    fs.mkdirSync(root, { recursive: true });
    const filename = `${new Date().toISOString().replace(/[:.]/g, '-')}-${workflowName}-${instanceId}.md`;
    const filePath = path.join(root, filename);
    const lines = [];
    lines.push(`# Workflow Debug Log`);
    lines.push(`- Workflow: ${workflowName}`);
    lines.push(`- Instance: ${instanceId}`);
    lines.push(`- Status: ${error ? 'failed' : 'completed'}`);
    lines.push(`- Time: ${new Date().toISOString()}`);
    lines.push('');
    lines.push('## Steps');
    const inst = workflowInstances.get(instanceId);
    if (inst && inst.steps) {
      for (const [sid, st] of Object.entries(inst.steps)) {
        lines.push(`- ${sid}: status=${st.status || 'unknown'}, attempts=${st.attempts || 0}, error=${st.error || 'none'}`);
      }
    }
    lines.push('');
    lines.push('## Results');
    lines.push('```json');
    lines.push(JSON.stringify(results || {}, null, 2));
    lines.push('```');
    if (error) {
      lines.push('');
      lines.push('## Error');
      lines.push(typeof error === 'string' ? error : (error?.message || 'unknown error'));
    }
    fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
  } catch (err) {
    if (WORKFLOW_DEBUG_MODE) {
      console.error('[WorkflowOrchestrator] Failed to write debug log:', err.message);
    }
  }
}

function parseOverrides(text) {
  const overrides = [];
  const regex = /<<WORKFLOW_OVERRIDE>>([\s\S]*?)<<END_WORKFLOW_OVERRIDE>>/g;
  let match;
  while ((match = regex.exec(text)) !== null) {
    const block = match[1];
    const parsed = {};
    block.split('\n').forEach(line => {
      const m = line.match(/^\s*([\w_]+)\s*:\s*(.+)$/);
      if (m) parsed[m[1].trim()] = m[2].trim();
    });
    if (parsed.action) overrides.push(parsed);
  }
  return overrides;
}

function applyOverrides(overrides, steps, currentStep) {
  for (const o of overrides) {
    if (o.action === 'add_step') {
      const newStep = {
        id: o.new_step_id,
        role: o.role,
        input_template: o.input || '',
        depend_on: o.after_step ? [o.after_step] : [],
        outputs: ['output']
      };
      if (!newStep.id || !newStep.role) continue;
      if (steps.find(s => s.id === newStep.id)) continue;
      const insertPos = o.after_step ? steps.findIndex(s => s.id === o.after_step) + 1 : steps.indexOf(currentStep) + 1;
      if (insertPos > 0 && insertPos < steps.length) steps.splice(insertPos, 0, newStep);
      else steps.push(newStep);
    } else if (o.action === 'skip_step' && o.target_step_id) {
      const idx = steps.findIndex(s => s.id === o.target_step_id);
      if (idx >= 0) steps.splice(idx, 1);
    } else if (o.action === 'change_role' && o.target_step_id && o.new_role) {
      const step = steps.find(s => s.id === o.target_step_id);
      if (step) step.role = o.new_role;
    }
  }
}

function configureWorkflow(args) {
  const { workflow_name, commander_agent, participant_agents, stages_text } = args;
  if (!workflow_name) throw new Error('workflow_name is required');
  if (!commander_agent) throw new Error('commander_agent is required');

  const wfDef = buildWorkflow({
    workflow_name,
    commander_agent,
    participant_agents: participant_agents || [],
    stages_text: stages_text || ''
  });

  const existingAgents = workflowsConfig.agents || [];
  const mergedAgents = [...existingAgents];
  const upsertAgent = (id, name) => {
    const found = mergedAgents.find(a => a.id === id);
    if (found) {
      found.agent_name = name;
      found.enabled = true;
    } else {
      mergedAgents.push({ id, agent_name: name, enabled: true });
    }
  };
  upsertAgent('commander', commander_agent);
  (participant_agents || []).forEach((name, idx) => {
    upsertAgent(`p${idx + 1}`, name);
  });

  workflowsConfig.agents = mergedAgents;
  workflowsConfig.workflows = workflowsConfig.workflows || {};
  workflowsConfig.workflows[workflow_name] = {
    commander_agent_name: commander_agent,
    role_map: wfDef.role_map,
    participants: wfDef.participants,
    steps: wfDef.steps,
    common_prompt: wfDef.common_prompt,
    retry_policy: wfDef.retry_policy,
    log_options: wfDef.log_options
  };

  saveWorkflows();
  return { status: 'success', result: `Workflow '${workflow_name}' configured.` };
}

module.exports = {
  initialize,
  processToolCall
};
