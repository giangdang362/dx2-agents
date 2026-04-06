import { writable } from 'svelte/store';

export interface OrchestrationStep {
	step: string;
	message: string;
	timestamp: number;
	elapsed_ms?: number;
	done: boolean;
	data?: Record<string, any>;
}

export interface PipelineNode {
	id: string;
	name: string;
	icon?: string;
	type: 'orchestrator' | 'worker';
	active: boolean;
	done: boolean;
}

export interface OrchestrationTokens {
	routing: { in: number; out: number };
	worker: { in: number; out: number };
}

export interface OrchestrationSession {
	session_id: string;
	steps: OrchestrationStep[];
	pipeline: PipelineNode[];
	start_time: number; // Date.now() when session started
	response_time_ms?: number;
	tokens?: OrchestrationTokens;
	status: 'idle' | 'routing' | 'active' | 'done';
}

export const orchestrationSession = writable<OrchestrationSession | null>(null);
export const showThinkingSidebar = writable(false);
