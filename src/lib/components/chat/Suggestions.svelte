<script lang="ts">
	import { parse } from 'yaml';
	import suggestionYaml from './suggestion.yml?raw';

	type SelectedModel = {
		id?: string;
		name?: string;
	} | null;

	type SuggestionQuestion = {
		content: string;
		category?: string;
	};

	type SuggestionConfigEntry = {
		category?: string;
		questions?: string[];
	};

	type SuggestionConfig = Record<string, SuggestionConfigEntry>;

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';
	export let onSelect = () => {};
	export let selectedModel: SelectedModel = null;

	const suggestionConfig: SuggestionConfig = (() => {
		try {
			const parsed = parse(suggestionYaml);

			if (parsed && typeof parsed === 'object') {
				return parsed as SuggestionConfig;
			}
		} catch (error) {
			console.error('Failed to parse suggestion.yml', error);
		}

		return {};
	})();

	// Fisher-Yates shuffle
	function shuffle<T>(arr: T[]): T[] {
		const a = [...arr];
		for (let i = a.length - 1; i > 0; i--) {
			const j = Math.floor(Math.random() * (i + 1));
			[a[i], a[j]] = [a[j], a[i]];
		}
		return a;
	}

	function normalizeAgentValue(value?: string) {
		return (value ?? '').trim().toLowerCase();
	}

	function getConfiguredQuestions(): SuggestionQuestion[] {
		return (suggestionPrompts ?? [])
			.map((prompt) => {
				if (typeof prompt === 'string') {
					return prompt;
				}

				return prompt?.content ?? '';
			})
			.map((content) => content.trim())
			.filter((content) => content.length > 0)
			.map((content) => ({ content }));
	}

	function getSelectedAgentKey(model: SelectedModel) {
		const modelId = normalizeAgentValue(model?.id);
		const modelName = normalizeAgentValue(model?.name);

		if (
			modelId === 'orchestrator' ||
			modelName === 'c-agents' ||
			modelName === 'c-agents orchestrator' ||
			modelName.includes('orchestrator')
		) {
			return 'orchestrator';
		}

		if (modelId === 'silicore' || modelName === 'silicore') {
			return 'silicore';
		}

		if (modelId === 'kinetix' || modelName === 'kinetix') {
			return 'kinetix';
		}

		if (
			modelId === 'meeting-room-agent' ||
			modelName === 'meeting room agent' ||
			modelName.includes('meeting room')
		) {
			return 'meeting-room-agent';
		}

		return null;
	}

	function getCuratedQuestions(agentKey: string): SuggestionQuestion[] {
		const config = suggestionConfig[agentKey];

		return (config?.questions ?? [])
			.filter((content): content is string => typeof content === 'string')
			.map((content) => content.trim())
			.filter((content) => content.length > 0)
			.map((content) => ({
				content,
				category: config?.category
			}));
	}

	function getOrchestratorQuestions(): SuggestionQuestion[] {
		const curatedAgentKeys = ['silicore', 'kinetix', 'meeting-room-agent'];

		return shuffle(
			curatedAgentKeys.flatMap((agentKey) => shuffle(getCuratedQuestions(agentKey)).slice(0, 2))
		);
	}

	function getQuestionsForSelectedAgent(model: SelectedModel): SuggestionQuestion[] {
		const agentKey = getSelectedAgentKey(model);

		if (agentKey === 'orchestrator') {
			return getOrchestratorQuestions();
		}

		if (agentKey) {
			return getCuratedQuestions(agentKey);
		}

		return getConfiguredQuestions();
	}

	function getCategoryClass(category?: string) {
		if (category === 'Semiconductor') {
			return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
		}

		if (category === 'Kinetix') {
			return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';
		}

		if (category === 'Meeting Room') {
			return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
		}

		return '';
	}

	let displayedQuestions: SuggestionQuestion[] = [];

	$: {
		if (inputValue.trim().length > 0) {
			displayedQuestions = [];
		} else {
			const questions = getQuestionsForSelectedAgent(selectedModel);
			displayedQuestions =
				getSelectedAgentKey(selectedModel) === 'orchestrator'
					? questions
					: shuffle(questions).slice(0, 4);
		}
	}
</script>

{#if displayedQuestions.length > 0}
	<div class="mb-1 flex gap-1 text-xs font-medium items-center text-gray-600 dark:text-gray-400">
		Suggested Questions
	</div>

	<div class="w-full">
		<div role="list" class="flex flex-col gap-1 {className}">
			{#each displayedQuestions as question, idx}
				<button
					class="waterfall flex items-start gap-2.5 w-full text-left
					       px-3 py-2.5 rounded-xl bg-transparent hover:bg-black/5
					       dark:hover:bg-white/5 transition group"
					style="animation-delay: {idx * 60}ms"
					on:click={() => onSelect({ type: 'prompt', data: question.content })}
				>
					{#if question.category}
						<span
							class="shrink-0 mt-0.5 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded {getCategoryClass(
								question.category
							)}"
						>
							{question.category}
						</span>
					{/if}
					<span
						class="text-sm dark:text-gray-300 dark:group-hover:text-gray-200 transition line-clamp-2"
					>
						{question.content}
					</span>
				</button>
			{/each}
		</div>
	</div>
{/if}

<style>
	@keyframes fadeInUp {
		0% {
			opacity: 0;
			transform: translateY(20px);
		}
		100% {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.waterfall {
		opacity: 0;
		animation-name: fadeInUp;
		animation-duration: 200ms;
		animation-fill-mode: forwards;
		animation-timing-function: ease;
	}
</style>
