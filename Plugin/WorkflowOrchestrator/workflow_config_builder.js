// Helper to build workflow definition from simple inputs (not exposed as plugin command)
function buildWorkflow({ workflow_name, commander_agent, participant_agents, stages_text }) {
  const lines = (stages_text || '').split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const participants = [];
  const role_map = {};

  if (commander_agent) {
    participants.push({ id: 'commander', agent_name: commander_agent, enabled: true });
    role_map['commander'] = commander_agent;
  }

  if (Array.isArray(participant_agents)) {
    participant_agents.forEach((name, idx) => {
      const id = `p${idx + 1}`;
      participants.push({ id, agent_name: name, enabled: true });
      role_map[id] = name;
    });
  }

  const steps = [];
  lines.forEach((text, idx) => {
    steps.push({
      id: `S${idx + 1}`,
      role: 'commander',
      input_template: text,
      outputs: ['output']
    });
  });

  return {
    workflow_name,
    commander_agent_name: commander_agent,
    role_map,
    participants: participants.map(p => p.id),
    steps,
    common_prompt: '请基于以下工作流阶段进行规划和指挥子 Agent 协作完成任务，如需调整流程可在对话中给出 WORKFLOW_OVERRIDE 指令。',
    retry_policy: {
      max_retries_per_step: 3,
      fallback_agent: commander_agent
    },
    log_options: {
      diary_folder: 'WorkflowDebugLogs',
      diary_tag: 'WorkflowDebug'
    }
  };
}

module.exports = { buildWorkflow };
