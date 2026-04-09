<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { user, showSidebar, WEBUI_NAME } from '$lib/stores';
	import { updateModelById, deleteModelById, getModelById } from '$lib/apis/models';
	import { getAgentsList } from '$lib/apis/agents';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import EditAgentModal from '$lib/components/admin/Agents/EditAgentModal.svelte';

	const i18n = getContext('i18n');

	let agents = [];
	let loading = true;
	let selectedAgent = null;
	let showEditModal = false;

	// Multi-select state
	let selectMode = false;
	let selectedIds = new Set<string>();
	let showDeleteConfirm = false;

	// Favorites state
	let favoriteIds: Set<string> = new Set();

	// Collapsible categories state
	let collapsedCategories: Set<string> = new Set();

	$: isAdmin = $user?.role === 'admin';

	onMount(async () => {
		if ($user?.role !== 'admin') {
			goto('/');
			return;
		}

		if (typeof localStorage !== 'undefined') {
			try {
				const raw = localStorage.getItem('agentHub:favorites');
				if (raw) favoriteIds = new Set(JSON.parse(raw));
			} catch {}

			try {
				const rawCollapsed = localStorage.getItem('agentHub:collapsedCategories');
				if (rawCollapsed) collapsedCategories = new Set(JSON.parse(rawCollapsed));
			} catch {}
		}

		await loadData();
	});

	function toggleFavorite(agentId: string) {
		if (favoriteIds.has(agentId)) {
			favoriteIds.delete(agentId);
		} else {
			favoriteIds.add(agentId);
		}
		favoriteIds = favoriteIds;
		try {
			localStorage.setItem('agentHub:favorites', JSON.stringify([...favoriteIds]));
		} catch {}
	}

	function toggleCategory(name: string) {
		if (collapsedCategories.has(name)) {
			collapsedCategories.delete(name);
		} else {
			collapsedCategories.add(name);
		}
		collapsedCategories = collapsedCategories;
		try {
			localStorage.setItem('agentHub:collapsedCategories', JSON.stringify([...collapsedCategories]));
		} catch {}
	}

	async function loadData() {
		loading = true;
		try {
			const res = await getAgentsList($user?.token);
			agents = (res ?? []).map((a) => ({
				...a,
				meta: {
					profile_image_url: a.profile_image_url || null,
					description: a.description || null,
					tags: a.tags ?? []
				}
			}));
		} catch (e) {
			toast.error($i18n.t('Failed to load agents'));
		} finally {
			loading = false;
		}
	}

	async function handleSaveAgent(event) {
		const model = event.detail;
		try {
			await updateModelById($user?.token, model.id, model);
			toast.success($i18n.t('Agent saved'));
			showEditModal = false;
			await loadData();
		} catch (e) {
			toast.error($i18n.t('Failed to save agent'));
		}
	}

	async function handleDeleteAgent(event) {
		try {
			await deleteModelById($user?.token, event.detail.id);
			toast.success($i18n.t('Agent deleted'));
			showEditModal = false;
			await loadData();
		} catch (e) {
			toast.error($i18n.t('Failed to delete agent'));
		}
	}

	async function handleEditAgent(agent: any) {
		if (!agent.workspace_model_id) return;
		try {
			const fullModel = await getModelById($user?.token, agent.workspace_model_id);
			if (!fullModel) {
				toast.error($i18n.t('Failed to load agent'));
				return;
			}
			selectedAgent = fullModel;
			showEditModal = true;
		} catch (e) {
			toast.error($i18n.t('Failed to load agent'));
		}
	}

	function isSelectable(agent) {
		return !!agent.workspace_model_id;
	}

	function handleCardClick(agent) {
		if (selectMode) return;
		sessionStorage.selectedModels = JSON.stringify([agent.id]);
		goto('/');
	}

	function toggleSelect(agent) {
		if (!isSelectable(agent)) return;
		if (selectedIds.has(agent.id)) {
			selectedIds.delete(agent.id);
		} else {
			selectedIds.add(agent.id);
		}
		selectedIds = selectedIds;
	}

	function toggleSelectAll() {
		const selectableAgents = agents.filter(isSelectable);
		if (selectedIds.size === selectableAgents.length) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(selectableAgents.map((a) => a.id));
		}
	}

	function exitSelectMode() {
		selectMode = false;
		selectedIds = new Set();
	}

	async function handleBulkDelete() {
		const ids = [...selectedIds].filter((id) => {
			const agent = agents.find((a) => a.id === id);
			return agent && isSelectable(agent);
		});
		if (ids.length === 0) return;
		try {
			await Promise.all(ids.map((id) => deleteModelById($user?.token, id)));
			toast.success($i18n.t(`Deleted ${ids.length} agent(s)`));
			exitSelectMode();
			await loadData();
		} catch (e) {
			toast.error($i18n.t('Failed to delete some agents'));
			await loadData();
		}
	}

	function isWorkspaceModel(agent) {
		return !!agent.workspace_model_id;
	}

	$: systemOnline = agents.some((a) => a.is_active);
	$: onlineCount = agents.filter((a) => a.is_active).length;

	// Group agents by their first tag; untagged agents fall into "General".
	// "General" is always rendered last; other categories are sorted alphabetically.
	// A synthetic "Favorites" category is prepended when any agents are favorited.
	$: agentCategories = (() => {
		const favorites = (agents as any[]).filter((a) => favoriteIds.has(a.id));

		const groups = new Map<string, any[]>();
		for (const agent of agents as any[]) {
			const tags = agent.meta?.tags ?? [];
			const categoryName = tags.length > 0 && tags[0]?.name ? tags[0].name : 'General';
			if (!groups.has(categoryName)) groups.set(categoryName, []);
			groups.get(categoryName)!.push(agent);
		}
		const regular = Array.from(groups.entries())
			.map(([name, items]) => ({ name, items, isFavorites: false }))
			.sort((a, b) => {
				if (a.name === 'General') return 1;
				if (b.name === 'General') return -1;
				return a.name.localeCompare(b.name);
			});

		if (favorites.length > 0) {
			return [{ name: 'Favorites', items: favorites, isFavorites: true }, ...regular];
		}
		return regular;
	})();

	const TAG_BADGE_CLASS = 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300';

	const SOURCE_BADGE = {
		workspace: { label: 'Workspace', class: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
		external: { label: 'External', class: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300' },
		function: { label: 'Function', class: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300' }
	};
</script>

<svelte:head>
	<title>Agents &bull; {$WEBUI_NAME}</title>
</svelte:head>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Agents')}
	message={$i18n.t(`Are you sure you want to delete ${selectedIds.size} agent(s)? This action cannot be undone.`)}
	onConfirm={handleBulkDelete}
/>

<EditAgentModal
	bind:show={showEditModal}
	model={selectedAgent}
	on:save={handleSaveAgent}
	on:delete={handleDeleteAgent}
/>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<div class="pb-1 px-3 md:px-[18px] flex-1 overflow-y-auto py-4">
		<!-- Header -->
		<div class="flex items-start justify-between mb-4">
			<div>
				<div class="flex items-center gap-3 mb-1">
					<h1 class="text-xl font-medium text-gray-900 dark:text-white">{$i18n.t('Agents Hub')}</h1>
					{#if !loading}
						<span
							class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium {systemOnline
								? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
								: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'}"
						>
							<span class="w-1.5 h-1.5 rounded-full {systemOnline ? 'bg-green-500' : 'bg-gray-400'}"></span>
							{systemOnline ? $i18n.t('System Online') : $i18n.t('System Offline')}
						</span>
					{/if}
				</div>
			</div>

			{#if isAdmin && !loading && agents.length > 0}
				<div class="flex items-center gap-2">
					{#if selectMode && selectedIds.size > 0}
						<button
							class="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-gray-900 text-sm font-medium transition"
							on:click={() => (showDeleteConfirm = true)}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
							</svg>
							{$i18n.t('Delete')}
						</button>
					{/if}
					{#if selectMode}
						<button
							class="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium transition text-gray-700 dark:text-gray-300"
							on:click={exitSelectMode}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
							</svg>
							{$i18n.t('Deselect All')}
						</button>
					{:else}
						<button
							class="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm font-medium transition text-gray-700 dark:text-gray-300"
							on:click={() => (selectMode = true)}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
							</svg>
							{$i18n.t('Select')}
						</button>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Agent Grid -->
		{#if loading}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-sm text-gray-400 dark:text-gray-500">{$i18n.t('Loading agents...')}</div>
			</div>
		{:else if agents.length === 0}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center">
					<div class="text-sm text-gray-400 dark:text-gray-500 mb-1">{$i18n.t('No agents found')}</div>
					<div class="text-xs text-gray-300 dark:text-gray-600">{$i18n.t('Create custom models in Workspace → Models to register agents.')}</div>
				</div>
			</div>
		{:else}
			{#each agentCategories as category (category.name)}
			{@const collapsed = collapsedCategories.has(category.name)}
			<section class="mb-8" class:mb-3={collapsed}>
				<button
					type="button"
					class="agent-section-header group flex items-center gap-2 mb-3 w-full text-left rounded-lg px-2 py-1.5 -mx-2 transition-colors"
					class:opacity-70={collapsed}
					on:click={() => toggleCategory(category.name)}
					aria-expanded={!collapsed}
					aria-controls="category-grid-{category.name}"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="2"
						stroke="currentColor"
						class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 shrink-0 transition-transform transition-colors duration-150 {collapsed ? '' : 'rotate-90'}"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
					</svg>
					{#if category.isFavorites}
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-yellow-400 shrink-0">
							<path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clip-rule="evenodd" />
						</svg>
					{/if}
					<h2 class="text-sm font-semibold text-gray-700 dark:text-gray-200 capitalize">
						{category.name}
					</h2>
					<span class="inline-flex items-center px-1.5 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 text-[11px] font-medium tabular-nums">
						{category.items.length}
					</span>
				</button>
			{#if !collapsed}
			<div id="category-grid-{category.name}" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-4">
				{#each category.items as agent (agent.id)}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="flex flex-col gap-3 p-4 rounded-2xl bg-white dark:bg-gray-800 border shadow-sm dark:shadow-gray-950/50 hover:shadow-md transition relative h-[10rem] cursor-pointer {selectedIds.has(agent.id)
							? 'border-blue-400 dark:border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800'
							: favoriteIds.has(agent.id)
							? 'border-yellow-300 dark:border-yellow-600/50 bg-yellow-50/30 dark:bg-yellow-900/5'
							: 'border-gray-200 dark:border-gray-600'}"
						on:click={() => {
							if (selectMode) {
								toggleSelect(agent);
							} else {
								handleCardClick(agent);
							}
						}}
					>
						<!-- Select checkbox -->
						{#if selectMode && isSelectable(agent)}
							<div class="absolute top-3 left-3 z-10">
								<div
									class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition {selectedIds.has(agent.id)
										? 'bg-blue-500 border-blue-500 text-white'
										: 'border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700'}"
								>
									{#if selectedIds.has(agent.id)}
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-3 h-3">
											<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
										</svg>
									{/if}
								</div>
							</div>
						{/if}

						<!-- Online dot -->
						<span
							class="absolute top-4 right-10 w-2.5 h-2.5 rounded-full {agent.is_active
								? 'bg-green-500'
								: 'bg-gray-300 dark:bg-gray-600'}"
						></span>

						<!-- Favorite star button -->
						{#if !selectMode}
							<button
								type="button"
								class="absolute top-3 right-3 p-0.5 rounded-md text-gray-400 hover:text-yellow-400 dark:text-gray-500 dark:hover:text-yellow-400 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition"
								title={favoriteIds.has(agent.id) ? $i18n.t('Unfavorite') : $i18n.t('Favorite')}
								on:click|stopPropagation={() => toggleFavorite(agent.id)}
							>
								{#if favoriteIds.has(agent.id)}
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4 text-yellow-400">
										<path fill-rule="evenodd" d="M10.788 3.21c.448-1.077 1.976-1.077 2.424 0l2.082 5.006 5.404.434c1.164.093 1.636 1.545.749 2.305l-4.117 3.527 1.257 5.273c.271 1.136-.964 2.033-1.96 1.425L12 18.354 7.373 21.18c-.996.608-2.231-.29-1.96-1.425l1.257-5.273-4.117-3.527c-.887-.76-.415-2.212.749-2.305l5.404-.434 2.082-5.005Z" clip-rule="evenodd" />
									</svg>
								{:else}
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z" />
									</svg>
								{/if}
							</button>
						{/if}

						<!-- Avatar + Name -->
						<div class="flex items-center gap-3 pr-5 {selectMode && isSelectable(agent) ? 'pl-6' : ''}">
							<img
								src={agent.meta?.profile_image_url || '/static/favicon.png'}
								alt={agent.name}
								class="w-10 h-10 rounded-full object-cover shrink-0"
							/>
							<div class="flex flex-col min-w-0">
								<span class="font-semibold text-sm text-gray-900 dark:text-white line-clamp-1">
									{agent.name}
								</span>
								<div class="flex flex-wrap min-w-0 gap-1">
									{#if agent.source && SOURCE_BADGE[agent.source]}
										<span
											class="inline-block text-[10px] font-medium uppercase px-2 py-0.5 mt-1 rounded-full {SOURCE_BADGE[agent.source].class}"
										>
											{$i18n.t(SOURCE_BADGE[agent.source].label)}
										</span>
									{/if}
									{#each agent.meta?.tags ?? [] as tag, i}
										{#if i < 2}
											<span class="inline-block text-[10px] font-medium uppercase px-2 py-0.5 mt-1 rounded-full {TAG_BADGE_CLASS}">
												{tag.name}
											</span>
										{:else if i === 2}
											<span class="inline-block text-[10px] font-medium px-2 py-0.5 mt-1 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
												+{(agent.meta?.tags ?? []).length - 2}
											</span>
										{/if}
									{/each}
								</div>
							</div>
						</div>

						<!-- Description -->
						<p class="flex-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-3 leading-relaxed overflow-hidden">
							{agent.meta?.description ?? ''}
						</p>

						<!-- Gear icon -->
						{#if isAdmin && !selectMode && agent.source !== 'function'}
							<button
								class="absolute bottom-3 right-3 p-1 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-700 transition"
								title={$i18n.t('Edit Agent')}
								on:click|stopPropagation={() => handleEditAgent(agent)}
							>
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
									<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
								</svg>
							</button>
						{/if}
					</div>
				{/each}
			</div>
			{/if}
			</section>
			{/each}
		{/if}

		<!-- Status Bar -->
		{#if !loading}
			<div class="flex items-center justify-between py-3 px-4 rounded-xl bg-gray-50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-850 text-xs text-gray-500 dark:text-gray-400">
				<div class="flex items-center gap-4">
					<span class="flex items-center gap-1.5">
						<span class="w-2 h-2 rounded-full bg-green-500"></span>
						{$i18n.t('Online')}
					</span>
					<span class="flex items-center gap-1.5">
						<span class="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></span>
						{$i18n.t('Offline')}
					</span>
				</div>
				<span>{agents.length} {$i18n.t('agents registered')}</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.agent-section-header {
		background: color-mix(in oklab, var(--color-gray-800, #333) 50%, transparent);
	}
	.agent-section-header:hover {
		background: color-mix(in oklab, var(--color-gray-700, #4b5563) 60%, transparent);
	}
</style>
