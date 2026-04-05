<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { orchestrationSession, showThinkingSidebar, showControls } from '$lib/stores';
	import { STEP_LABELS } from '$lib/utils/orchestration-ws';

	const i18n: Writable<i18nType> = getContext('i18n');

	$: session = $orchestrationSession;
	$: steps = session?.steps || [];
	$: isDone = session?.status === 'done';
	$: responseTimeMs = session?.response_time_ms || 0;

	function formatTime(ms: number): string {
		if (ms >= 1000) {
			return `${(ms / 1000).toFixed(1)}s`;
		}
		return `${ms}ms`;
	}

	function getStepLabel(step: string): { title: string; source: string } {
		return STEP_LABELS[step] || { title: step.toUpperCase().replace(/_/g, ' '), source: 'System' };
	}

	function close() {
		showThinkingSidebar.set(false);
		showControls.set(false);
	}
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-800">
	<!-- Header -->
	<div class="flex items-center justify-between px-4 py-3 border-b border-gray-100 dark:border-gray-700/50">
		<div class="flex items-center gap-2">
			<h3 class="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
				{#if isDone}
					{$i18n.t('Thinking')}
				{:else}
					{$i18n.t('Thinking...')}
				{/if}
			</h3>
			{#if !isDone && steps.length > 0}
				<span class="relative flex h-2 w-2">
					<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
					<span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
				</span>
			{/if}
		</div>
		<button
			class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 transition"
			on:click={close}
			aria-label={$i18n.t('Close')}
		>
			<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M9 18l6-6-6-6" />
			</svg>
		</button>
	</div>

	<!-- Steps list -->
	<div class="flex-1 overflow-y-auto px-3 py-3 space-y-1 scrollbar-hidden">
		{#each steps as step, idx (idx)}
			{@const label = getStepLabel(step.step)}
			{@const isLast = idx === steps.length - 1}
			{@const isActive = isLast && !step.done && !isDone}
			<div class="relative pl-5 pb-2">
				<!-- Vertical line -->
				{#if idx < steps.length - 1}
					<div
						class="absolute left-[7px] top-[14px] bottom-0 w-px bg-gray-200 dark:bg-gray-700"
					></div>
				{/if}

				<!-- Status dot -->
				<div class="absolute left-0 top-[6px]">
					{#if isActive}
						<span class="relative flex h-3.5 w-3.5">
							<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-50"></span>
							<span class="relative inline-flex rounded-full h-3.5 w-3.5 bg-yellow-400 border-2 border-white dark:border-slate-800"></span>
						</span>
					{:else if step.done || isDone}
						<span class="flex h-3.5 w-3.5 rounded-full bg-green-500 border-2 border-white dark:border-slate-800"></span>
					{:else}
						<span class="flex h-3.5 w-3.5 rounded-full bg-gray-300 dark:bg-gray-600 border-2 border-white dark:border-slate-800"></span>
					{/if}
				</div>

				<!-- Step content -->
				<div class="min-w-0">
					<!-- Source badge + title -->
					<div class="flex items-center gap-1.5 mb-0.5">
						<span
							class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider
								{label.source === 'Router'
								? 'bg-blue-500/15 text-blue-400'
								: label.source === 'Agent'
									? 'bg-purple-500/15 text-purple-400'
									: 'bg-gray-500/15 text-gray-400'}"
						>
							{label.source}
						</span>
					</div>
					<div class="flex items-center gap-1.5">
						<span class="text-[11px] font-semibold text-gray-700 dark:text-gray-300 tracking-wide">
							{#if step.step === 'specialist_match' && step.data?.agent_name}
								{label.title}: {step.data.agent_name}
							{:else}
								{label.title}
							{/if}
						</span>
						{#if step.elapsed_ms != null}
							<span class="text-[9px] text-gray-400 dark:text-gray-500 tabular-nums">
								{formatTime(step.elapsed_ms)}
							</span>
						{/if}
					</div>

					<!-- Description -->
					{#if step.message}
						<p class="text-[10px] text-gray-500 dark:text-gray-500 mt-0.5 leading-relaxed break-words">
							{step.message}
						</p>
					{/if}

					<!-- Keyword matches detail -->
					{#if step.data?.keyword_matches?.length > 0}
						<div class="mt-1 flex flex-wrap gap-1">
							{#each step.data?.keyword_matches ?? [] as match}
								<span class="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] bg-green-500/10 text-green-400">
									{match.agent_name}
									{#if match.matched_tags?.length > 0}
										({match.matched_tags.join(', ')})
									{/if}
								</span>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		{/each}

		{#if steps.length === 0}
			<div class="flex flex-col items-center justify-center h-full gap-2 text-gray-400 dark:text-gray-500 text-xs px-4 text-center">
				<svg class="w-8 h-8 opacity-30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M12 2a8 8 0 0 0-8 8c0 3.4 2.1 6.3 5 7.4V19a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1v-1.6c2.9-1.1 5-4 5-7.4a8 8 0 0 0-8-8Z" />
					<path d="M10 22h4" />
				</svg>
				<span>{$i18n.t('Send a message to see agent thinking steps here.')}</span>
			</div>
		{/if}
	</div>

	<!-- Footer: Response time + Tokens -->
	{#if isDone || steps.length > 0}
		<div class="border-t border-gray-100 dark:border-gray-700/50 px-4 py-2.5">
			<div class="flex items-center justify-between text-[10px] uppercase tracking-wider">
				<div class="flex items-center gap-1.5">
					<span class="font-semibold text-gray-400 dark:text-gray-500">{$i18n.t('Response Time')}</span>
					<span class="font-bold tabular-nums text-gray-600 dark:text-gray-300">
						{responseTimeMs ? formatTime(responseTimeMs) : '...'}
					</span>
				</div>
			</div>
		</div>
	{/if}
</div>
