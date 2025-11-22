const WorkflowOrchestrator = require('./WorkflowOrchestrator.js');

// Mock dependencies
const mockConfig = {
    WORKFLOW_DEBUG_MODE: true
};

const mockDependencies = {
    vcpLogFunctions: {
        pushVcpInfo: (data) => console.log('[MockVCPLog]', JSON.stringify(data, null, 2))
    },
    PluginManager: {
        processToolCall: async (toolName, args) => {
            console.log(`[MockPluginManager] Called ${toolName} with:`, args);
            if (toolName === 'AgentAssistant') {
                return { status: 'success', result: `Mock response from ${args.agent_name} for prompt: ${args.prompt.substring(0, 20)}...` };
            }
            return { status: 'error', error: 'Unknown tool' };
        }
    }
};

async function runTest() {
    console.log('--- Initializing ---');
    WorkflowOrchestrator.initialize(mockConfig, mockDependencies);

    console.log('--- Starting Workflow ---');
    const result = await WorkflowOrchestrator.processToolCall({
        command: 'StartWorkflow',
        workflow_name: 'GenericTaskFlow',
        user_task: 'Test Task',
        session_id: 'test_session'
    });

    console.log('--- Start Result ---', result);

    // Wait for async execution to complete (simulated)
    // Since executeWorkflow is not awaited in startWorkflow, we need to wait a bit
    await new Promise(resolve => setTimeout(resolve, 2000));
}

runTest();
