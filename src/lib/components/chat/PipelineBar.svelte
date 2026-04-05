<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { orchestrationSession, models } from '$lib/stores';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let selectedModels: string[] = [];

	$: isOrchestrator = selectedModels.some((id) => {
		const model = $models.find((m) => m.id === id);
		return (model?.owned_by as string) === 'orchestrator';
	});

	$: session = $orchestrationSession;

	$: pipeline = (() => {
		if (session && session.pipeline.length > 0) {
			return session.pipeline;
		}
		// Direct agent mode — single node
		if (!isOrchestrator && selectedModels.length > 0) {
			const model = $models.find((m) => m.id === selectedModels[0]);
			if (model) {
				return [
					{
						id: model.id,
						name: model.name,
						icon: '',
						type: 'worker' as const,
						active: false,
						done: false
					}
				];
			}
		}
		// Orchestrator idle
		if (isOrchestrator) {
			return [
				{
					id: 'orchestrator',
					name: 'General Assistant',
					icon: '⚙️',
					type: 'orchestrator' as const,
					active: false,
					done: false
				}
			];
		}
		return [];
	})();

	$: isRouting = session?.status === 'routing';
</script>

{#if pipeline.length > 0}
	<div
		class="flex items-center gap-2 px-4 py-2 border-b border-gray-100 dark:border-gray-800/50 bg-white/50 dark:bg-gray-900/50 backdrop-blur-sm"
	>
		<span class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 shrink-0">
			{$i18n.t('Agent Pipeline')}
		</span>

		<div class="flex items-center gap-1 overflow-x-auto">
			{#each pipeline as node, idx (node.id)}
				{#if idx > 0}
					<!-- Connector dots -->
					<div class="flex items-center gap-0.5 px-1 shrink-0">
						<span
							class="block w-1 h-1 rounded-full {isRouting
								? 'bg-blue-400 animate-pulse'
								: 'bg-gray-400 dark:bg-gray-600'}"
						></span>
						<span
							class="block w-1 h-1 rounded-full {isRouting
								? 'bg-blue-400 animate-pulse [animation-delay:150ms]'
								: 'bg-gray-400 dark:bg-gray-600'}"
						></span>
						<span
							class="block w-1 h-1 rounded-full {isRouting
								? 'bg-blue-400 animate-pulse [animation-delay:300ms]'
								: 'bg-gray-400 dark:bg-gray-600'}"
						></span>
					</div>
				{/if}

				<!-- Node -->
				<div
					class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 transition-all duration-300
						{node.active
						? 'bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/30'
						: node.done
							? 'bg-green-500/10 text-green-400 ring-1 ring-green-500/20'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 ring-1 ring-gray-200 dark:ring-gray-700'}"
				>
					{#if node.type === 'orchestrator'}
						<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
							<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
						</svg>
					{:else}
						<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 8V4H8" />
							<rect width="16" height="12" x="4" y="8" rx="2" />
							<path d="M2 14h2" />
							<path d="M20 14h2" />
							<path d="M15 13v2" />
							<path d="M9 13v2" />
						</svg>
					{/if}
					<span class="hidden sm:inline">{node.name}</span>
				</div>
			{/each}

			{#if isRouting && pipeline.length === 1}
				<!-- Placeholder for incoming agent -->
				<div class="flex items-center gap-0.5 px-1 shrink-0">
					<span class="block w-1 h-1 rounded-full bg-blue-400 animate-pulse"></span>
					<span class="block w-1 h-1 rounded-full bg-blue-400 animate-pulse [animation-delay:150ms]"></span>
					<span class="block w-1 h-1 rounded-full bg-blue-400 animate-pulse [animation-delay:300ms]"></span>
				</div>
				<div
					class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 ring-1 ring-gray-200 dark:ring-gray-700 ring-dashed"
				>
					<svg class="w-3.5 h-3.5 shrink-0 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="12" cy="12" r="10" />
						<path d="M8 12h8" />
					</svg>
					<span class="hidden sm:inline">{$i18n.t('Selecting...')}</span>
				</div>
			{/if}
		</div>
	</div>
{/if}
