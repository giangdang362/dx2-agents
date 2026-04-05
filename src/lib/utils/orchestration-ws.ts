import { get } from 'svelte/store';
import { WEBUI_HOSTNAME } from '$lib/constants';
import {
	orchestrationSession,
	showThinkingSidebar,
	showControls,
	type OrchestrationSession,
	type OrchestrationStep,
	type PipelineNode
} from '$lib/stores';

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;
const MAX_RECONNECT_DELAY = 30000;

const STEP_LABELS: Record<string, { title: string; source: string }> = {
	session_start: { title: 'ANALYZING MESSAGE', source: 'Router' },
	evaluating_triggers: { title: 'EVALUATING TRIGGERS', source: 'Router' },
	ai_analysis: { title: 'DECISION: AI ANALYSIS', source: 'Router' },
	specialist_match: { title: 'SPECIALIST MATCH', source: 'Router' },
	no_specialist_match: { title: 'NO SPECIALIST MATCH', source: 'Router' },
	agent_active: { title: 'PROCESSING', source: 'Agent' },
	agent_done: { title: 'RESPONSE COMPLETE', source: 'Agent' },
	session_done: { title: 'SESSION COMPLETE', source: 'System' },
	// Common status actions from all model types
	status: { title: 'STATUS UPDATE', source: 'Agent' },
	processing: { title: 'PROCESSING', source: 'Agent' },
	calling_agent: { title: 'CALLING AGENT', source: 'Agent' },
	calling_llm: { title: 'CALLING LLM', source: 'Agent' },
	analyzing: { title: 'ANALYZING', source: 'Agent' },
	extracting_info: { title: 'EXTRACTING INFO', source: 'Agent' },
	loading_context: { title: 'LOADING CONTEXT', source: 'Agent' },
	complete: { title: 'COMPLETE', source: 'Agent' },
	web_search: { title: 'WEB SEARCH', source: 'Agent' },
	knowledge_search: { title: 'KNOWLEDGE SEARCH', source: 'Agent' },
	web_search_queries_generated: { title: 'SEARCH QUERIES GENERATED', source: 'Agent' },
	queries_generated: { title: 'QUERIES GENERATED', source: 'Agent' },
	sources_retrieved: { title: 'SOURCES RETRIEVED', source: 'Agent' }
};

function processEvent(event: Record<string, any>) {
	const { step, session_id } = event;

	if (step === 'connected' || step === 'ping') return;

	const current = get(orchestrationSession);

	if (step === 'session_start') {
		// New session — reset
		const newSession: OrchestrationSession = {
			session_id,
			start_time: Date.now(),
			steps: [
				{
					step,
					message: event.message || 'Analyzing your request...',
					timestamp: event.timestamp,
					elapsed_ms: event.elapsed_ms || 0,
					done: false,
					data: { agent_count: event.agent_count, start_time: event.start_time }
				}
			],
			pipeline: [
				{
					id: 'orchestrator',
					name: 'General Assistant',
					icon: '⚙️',
					type: 'orchestrator',
					active: true,
					done: false
				}
			],
			status: 'routing'
		};
		orchestrationSession.set(newSession);

		// Auto-open thinking sidebar
		showThinkingSidebar.set(true);
		showControls.set(true);
		return;
	}

	if (!current || current.session_id !== session_id) return;

	// Mark previous in-progress step as done
	const steps = current.steps.map((s) => (s.done ? s : { ...s, done: true }));

	const doneSteps = ['session_done', 'agent_done'];
	const isTerminal = doneSteps.includes(step);

	if (step === 'agent_active') {
		// Add worker node to pipeline
		const pipeline: PipelineNode[] = [
			{ ...current.pipeline[0], active: false, done: true },
			{
				id: event.agent_id,
				name: event.agent_label || event.agent_id,
				icon: event.agent_icon || '🤖',
				type: 'worker',
				active: true,
				done: false
			}
		];

		steps.push({
			step,
			message: event.message || `Delegated to ${event.agent_label}`,
			timestamp: event.timestamp,
			elapsed_ms: event.elapsed_ms,
			done: false,
			data: { agent_id: event.agent_id, agent_label: event.agent_label }
		});

		orchestrationSession.set({
			...current,
			steps,
			pipeline,
			status: 'active'
		});
		return;
	}

	if (step === 'agent_done') {
		const pipeline = current.pipeline.map((n) => ({ ...n, active: false, done: true }));

		steps.push({
			step,
			message: event.message || 'Response complete',
			timestamp: event.timestamp,
			elapsed_ms: event.elapsed_ms,
			done: true,
			data: {
				worker_tokens: event.worker_tokens,
				routing_tokens: event.routing_tokens
			}
		});

		orchestrationSession.set({
			...current,
			steps,
			pipeline,
			tokens: {
				routing: event.routing_tokens || { in: 0, out: 0 },
				worker: event.worker_tokens || { in: 0, out: 0 }
			},
			status: 'done'
		});
		return;
	}

	if (step === 'session_done') {
		const pipeline = current.pipeline.map((n) => ({ ...n, active: false, done: true }));

		orchestrationSession.set({
			...current,
			steps,
			pipeline,
			response_time_ms: event.response_time_ms,
			tokens: event.total_tokens || current.tokens,
			status: 'done'
		});
		return;
	}

	// Generic step (evaluating_triggers, ai_analysis, specialist_match, no_specialist_match)
	steps.push({
		step,
		message: event.message || '',
		timestamp: event.timestamp,
		elapsed_ms: event.elapsed_ms,
		done: isTerminal,
		data: {
			keyword_matches: event.keyword_matches,
			trigger_count: event.trigger_count,
			agent_id: event.agent_id,
			agent_name: event.agent_name,
			routing_tokens: event.routing_tokens,
			agents: event.agents
		}
	});

	orchestrationSession.set({
		...current,
		steps,
		status: current.status
	});
}

export function connectOrchestrationWS() {
	if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
		return;
	}

	const hostname = WEBUI_HOSTNAME || location.host;
	const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
	const url = `${protocol}//${hostname}/api/v1/orchestration/ws`;

	try {
		ws = new WebSocket(url);

		ws.onopen = () => {
			reconnectDelay = 1000;
		};

		ws.onmessage = (e) => {
			try {
				const data = JSON.parse(e.data);
				processEvent(data);
			} catch {
				// ignore parse errors
			}
		};

		ws.onclose = () => {
			scheduleReconnect();
		};

		ws.onerror = () => {
			if (ws) {
				ws.onclose = null;
				ws.close();
				ws = null;
			}
			scheduleReconnect();
		};
	} catch {
		scheduleReconnect();
	}
}

function scheduleReconnect() {
	if (reconnectTimer) return;
	reconnectTimer = setTimeout(() => {
		reconnectTimer = null;
		reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY);
		connectOrchestrationWS();
	}, reconnectDelay);
}

export function disconnectOrchestrationWS() {
	if (reconnectTimer) {
		clearTimeout(reconnectTimer);
		reconnectTimer = null;
	}
	if (ws) {
		ws.onclose = null;
		ws.onerror = null;
		ws.close();
		ws = null;
	}
	reconnectDelay = 1000;
}

export function resetOrchestrationSession() {
	orchestrationSession.set(null);
}

/**
 * For direct agent chats (non-orchestrator), create a simple session
 * so the ThinkingSidebar can show status events.
 */
export function startDirectAgentSession(agentId: string, agentName: string) {
	const now = Date.now();
	const session_id = `direct-${now}`;
	orchestrationSession.set({
		session_id,
		start_time: now,
		steps: [
			{
				step: 'agent_active',
				message: `Processing with ${agentName}...`,
				timestamp: now / 1000,
				elapsed_ms: 0,
				done: false,
				data: { agent_id: agentId, agent_label: agentName }
			}
		],
		pipeline: [
			{
				id: agentId,
				name: agentName,
				icon: '🤖',
				type: 'worker',
				active: true,
				done: false
			}
		],
		status: 'active'
	});

	// Auto-open thinking sidebar
	showThinkingSidebar.set(true);
	showControls.set(true);
}

export function pushDirectAgentStep(action: string, description: string) {
	let current = get(orchestrationSession);

	// Auto-create session if none exists
	if (!current) {
		const now = Date.now();
		current = {
			session_id: `direct-${now}`,
			start_time: now,
			steps: [],
			pipeline: [],
			status: 'active'
		};
		// Auto-open thinking sidebar
		showThinkingSidebar.set(true);
		showControls.set(true);
	}

	// Mark previous steps as done
	const steps = current.steps.map((s) => (s.done ? s : { ...s, done: true }));

	steps.push({
		step: action,
		message: description,
		timestamp: Date.now() / 1000,
		elapsed_ms: Date.now() - current.start_time,
		done: false,
		data: {}
	});

	orchestrationSession.set({
		...current,
		steps
	});
}

export function completeDirectAgentSession(info?: { prompt_tokens?: number; completion_tokens?: number }) {
	const current = get(orchestrationSession);
	if (!current) return;

	const steps = current.steps.map((s) => ({ ...s, done: true }));
	const pipeline = current.pipeline.map((n) => ({ ...n, active: false, done: true }));

	const workerIn = info?.prompt_tokens ?? 0;
	const workerOut = info?.completion_tokens ?? 0;
	const responseTimeMs = Date.now() - current.start_time;

	orchestrationSession.set({
		...current,
		steps,
		pipeline,
		status: 'done',
		response_time_ms: responseTimeMs,
		tokens: {
			routing: { in: 0, out: 0 },
			worker: { in: workerIn, out: workerOut }
		}
	});
}

export { STEP_LABELS };
