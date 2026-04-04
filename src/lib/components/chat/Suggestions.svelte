<script lang="ts">
	type SelectedModel = {
		id?: string;
		name?: string;
	} | null;

	type SuggestionQuestion = {
		content: string;
		category?: string;
	};

	export let suggestionPrompts = [];
	export let className = '';
	export let inputValue = '';
	export let onSelect = () => {};
	export let selectedModel: SelectedModel = null;

	const SEMICONDUCTOR_QUESTIONS = [
		'What was the approximate size of the global logic IC market in 2024, and what is it projected to reach in 2025?',
		'How many cores does the AMD EPYC 9965P (Turin) processor have, what process node is it manufactured on, and what is its TDP?',
		'What are the FP32 TFLOPS, HBM capacity, and memory bandwidth of the NVIDIA H100 GPU?',
		'What are the FP32 TFLOPS, HBM capacity, and memory bandwidth of the NVIDIA B200 (Blackwell) GPU?',
		'What approximate share of the AI accelerator market does NVIDIA hold?',
		'What is the projected size of the SoC market in 2025 and 2032?',
		'What is the ASIC market size in 2024 and its projected size by 2030?',
		'What JEDEC standard defines DDR4 SDRAM? What about DDR5?',
		'What are the bandwidth specifications for HBM3, HBM3e (12-high stack), and HBM4?',
		'What is the interface width and maximum capacity planned for HBM4?',
		'What is the maximum data rate for LPDDR5X and the estimated data rate for LPDDR6?',
		'How many NAND layers has Samsung achieved in mass production (as of April 2024), and how many has SK Hynix achieved with 4D NAND (as of November 2024)?',
		'What are the DRAM market shares for Samsung, SK Hynix, and Micron in 2024?',
		'What are the HBM market shares for SK Hynix, Samsung, and Micron in 2024?',
		'What is the NAND market share of Samsung and SK Group in 2024?',
		'What is the size of the analog IC market and the mixed-signal IC market in 2024?',
		'What is the PMIC market size in 2024 and its projection for 2034?',
		'What are the analog IC market shares for Texas Instruments and Analog Devices?',
		'What is the typical open-loop gain range for operational amplifiers?',
		'What bit range, sample rate range, and SNR range are typical for ADCs?',
		'What is the RFIC market size in 2024 and its CAGR to 2035?',
		'What percentage of the RF semiconductor market do RF power amplifiers represent?',
		'What automotive safety integrity level (ASIL) do automotive PMICs typically conform to, and per which standard?',
		'What is the ARM MCU market size in 2024?',
		'What is the automotive MCU market size in 2024?',
		'What is the RISC-V market size in 2024 and its CAGR?',
		'How many RISC-V cores had been shipped by 2022?',
		'What percentage of semiconductor devices per vehicle do MCUs represent, and how does this change in EVs?',
		'What product longevity guarantee does NXP provide for the S32K family?',
		'What is the measurement range for MEMS accelerometers and gyroscopes?',
		'What is the data rate per lane of the MIPI A-PHY standard used for automotive camera serialization?',
		'What was the AI infrastructure market size in 2024, and how much was spent on AI in H1 2024?',
		'What are the key specifications of the NVIDIA DGX H100 system (GPU count, RAM, power, TFLOPS)?',
		'What are the key specifications of the NVIDIA GB200 NVL72 system (GPU/CPU count, compute, HBM capacity)?',
		'What is the switching capacity of the Broadcom Tomahawk 5?',
		'What is the bandwidth and SDK of the NVIDIA BlueField-3 DPU?',
		'What is the SmartNIC/DPU market size in 2024?',
		'What is the compute performance of the NVIDIA Jetson Orin embedded platform?',
		'What purity level is required for semiconductor-grade silicon, and what method is used to grow silicon ingots?',
		'What are the three standard silicon wafer diameters used in semiconductor manufacturing?',
		'What is the bandgap and breakdown field strength of 4H-SiC?',
		'What is the bandgap, breakdown field strength, and 2DEG mobility of GaN?',
		'What is the global silicon wafer market size in 2024?',
		'What percentage of silicon wafer production is 300mm?',
		'Which company is the #1 silicon wafer vendor by revenue?',
		'How much CHIPS Act funding did GlobalWafers receive?',
		'What is the global SiC market size range in 2024 and its CAGR range?',
		"What is Wolfspeed's approximate global SiC market share, and how many wafers do they produce?",
		'By how much can SiC extend battery range in EVs and reduce DC fast charging time?',
		'How much more die area does a 200mm SiC wafer provide compared to 150mm?',
		'What is the electron mobility of GaAs?',
		'What are the common dopant gas sources for Boron, Phosphorus, and Arsenic in ion implantation?',
		'What is the energy range and dose range for ion implantation?',
		'What are the IDLH and OSHA PEL values for phosphine (PH3)?',
		'What are the IDLH and OSHA PEL values for arsine (AsH3)?',
		'What is the dielectric constant (k) of HfO2, Al2O3, and ZrO2?',
		'What is the dielectric constant of SiO2 and Si3N4?',
		'What is the dielectric constant range for porous SiCOH, and for which technology nodes is it used?',
		'What are the resistivities of Copper, Tungsten, Cobalt, and Ruthenium used in BEOL interconnects?',
		'For which technology nodes is Ruthenium considered as a barrier-free interconnect metal?',
		'What temperature range and duration is typical for rapid thermal annealing (RTA)?',
		'What are the exposure wavelengths and minimum resolution for g-line, i-line, KrF, ArF dry, ArF immersion, and EUV lithography?',
		'In a chemically amplified resist (CAR), how many deprotection events can one photon trigger?',
		'What is the line edge roughness (LER) of metal oxide resists (MOR), and for which lithography are they preferred?',
		'What is the etch rate of HF on SiO2, and what hazard class is HF?',
		'What is the selectivity of hot H3PO4 at 160C for etching Si3N4 over SiO2?',
		'What abrasive material and pH range are used for STI CMP slurry?',
		'What is the composition of Piranha solution, and what is it used for?',
		'When was the RCA clean process introduced, and what are its two steps?',
		'What is the projected EUV resist market size by 2030?',
		'What is the chemical formula of TEOS and what film does it deposit?',
		'What precursor is used for ALD deposition of HfO2?',
		'What is the typical growth rate per cycle in ALD?',
		'What precursor gas is used for CVD tungsten deposition?',
		'What is the ALD precursor for Al2O3 and what is its chemical formula?',
		'What is the glass transition temperature (Tg) of standard FR-4 and high-Tg FR-4?',
		'What is the Tg of Rogers RO4003C substrate, and what is it used for?',
		'What is the composition and melting temperature of SAC305 solder?',
		'What is the typical thermal conductivity range of thermal interface materials (TIM)?',
		'How many process steps are typically needed for a 300mm 5nm logic wafer, and what is the typical cycle time?',
		'What are the dry and wet thermal oxidation rates of silicon at 900C?',
		'What numerical aperture (NA) does High-NA EUV use, and for which nodes is it intended?',
		'What are the temperature ranges for APCVD, LPCVD, and PECVD?',
		'How many copper wiring layers are typical in BEOL, and what process is used?',
		'What metals are used for local interconnect (M0-M2) at advanced nodes?',
		'What is the approximate blade dicing kerf width?',
		'What yield and defect density targets are expected for mature process nodes?',
		'What are the CD uniformity (CDU) and overlay targets for EUV lithography?',
		'Name four electrical parameters tested during wafer-level testing (EDS).',
		'What is the typical lamination temperature in PCB fabrication?',
		'What are typical pick-and-place machine speeds and placement accuracy?',
		'What is the reflow soldering temperature profile for lead-free SMT?',
		'What IPC standard defines electronic assembly acceptability?',
		'What IPC standard defines soldering requirements?',
		'What wave soldering temperature is used for through-hole components?',
		'What JEDEC standard governs moisture sensitivity for components?',
		'What standard governs ESD control programs in electronics manufacturing?',
		'What is the typical capital investment for a leading-edge 300mm wafer fab?',
		'What was the approximate global wafer processing equipment market in 2023?',
		'Which company is the sole supplier of EUV lithography scanners?',
		'What is the cost range for an EUV scanner?',
		'What is the throughput of the ASML NXE:3600D EUV scanner?',
		'Name the two leading ATE (automated test equipment) vendors.',
		'What is the target on-time delivery (OTD) KPI in semiconductor supply chains?',
		'What is the incoming quality target in PPM (parts per million)?',
		'What is the recommended safety stock level for long-lead semiconductor materials?',
		'What is the best-in-class PO cycle time according to the Hackett Group?',
		'What are the most common Incoterms used in semiconductor procurement?',
		'What does the payment term "2/10 Net 30" mean?',
		'What JEDEC standard series covers component reliability testing?',
		'What automotive reliability qualification standard is commonly referenced for ICs?',
		'What do IQC, IPQC, and OQC stand for in quality management?',
		'What ISO standard defines cleanroom classifications?',
		'What ISO cleanroom class is typical for semiconductor fabs?',
		'What are the typical cleanroom temperature tolerance and humidity range?',
		'What HS code is used for electronic integrated circuits?',
		'What JEDEC standard governs moisture-sensitive device packaging for shipping?',
		'What ISTA standard covers cold-chain shipping?',
		'What EU directive governs the restriction of hazardous substances in electronics (RoHS)?',
		'What safety standard applies to audio/video and information technology equipment?',
		'What U.S. agency and regulatory framework govern semiconductor export controls?',
		'What environmental management system standard is referenced for semiconductor fabs?',
		'What is the typical warranty period for semiconductor products?',
		'What does RMA stand for?',
		'What automotive quality management standard is referenced alongside AEC-Q100?',
		'What structured problem-solving methodology is used in semiconductor failure analysis?',
		'What do FAE and NRE stand for in the context of customer support?',
		'What metric is used to gauge demand health in the semiconductor market (ratio of orders to shipments)?',
		'What does LTA stand for in semiconductor pricing?',
		'What are the three main semiconductor sales channels?',
		'What are the two primary 2.5D packaging technologies from TSMC and Intel?',
		'What does UCIE stand for, and what is its purpose?',
		'What does KGD stand for, and why is it important in chiplet packaging?',
		'What interconnect technology is used in 3D IC stacking (e.g., HBM)?',
		'What was the total global semiconductor market revenue in 2024 according to SIA?',
		'What are the three plasma etch chemistries for: (a) silicon, (b) polysilicon, and (c) SiO2?',
		'What dilution ratio is used for HF dip to remove native oxide?',
		'Name the top four photoresist vendors.',
		'What is the combined market share of the top 5 silicon wafer vendors?'
	];

	const KINETIX_QUESTIONS = [
		'What distinguishes a direct drive system from a traditional indirect drive system?',
		'Why does ball screw critical speed (whip frequency) pose a limitation that direct drive technology eliminates?',
		'Compare ironcore and ironless linear motors across the following parameters: cogging force, normal (attraction) force, moving mass, and thermal dissipation capability.',
		'Why are Voice Coil Motors (VCMs) considered ideal for direct force control applications, and what are their typical stroke and bandwidth capabilities?',
		'What are the two main construction types of Direct Drive Rotary (DDR) motors, and when would each be preferred?',
		'Define Abbe Error, provide its formula, and calculate the error for a system where the encoder is mounted 100 mm below the workpiece and the carriage has 5 urad of pitch error.',
		'What is the main control challenge of an XY gantry (H-bridge) configuration, and why does it arise?',
		'Explain the relationship between winding insulation class, motor temperature, and insulation lifetime. What is the Arrhenius rule of thumb for insulation degradation?',
		'A horizontal linear stage has a payload of 10 kg, carriage + motor mass of 5 kg, and 20 N of friction force. The trapezoidal motion profile specifies 5 m/s2 acceleration over 0.2 s, 0.6 s cruise at 1 m/s, and 0.2 s deceleration, for a 1 s total cycle. Calculate the required RMS force and determine the minimum motor continuous force rating with a 25% safety margin.',
		'What critical precaution must be observed when setting the coolant temperature in a liquid-cooled direct drive motor system?',
		'Describe the three main types of optical encoder sensing mechanisms and explain which achieves the finest resolution.',
		'Rank the four magnetic sensor element types (Hall Effect, AMR, GMR, TMR) from lowest to highest resolution, and explain the operating principle of TMR sensors.',
		'Explain the key differences between resolution, repeatability, and accuracy in a positioning system. Can a system be highly repeatable but inaccurate?',
		'What happens to position knowledge when power is lost for an incremental encoder versus an absolute encoder?',
		'Describe the step-by-step error mapping procedure using a laser interferometer. What is the fundamental limitation of error compensation?',
		'Compare the EnDat 2.2 and BiSS-C encoder protocols in terms of directionality, error detection, and openness of standard.',
		'Why must environmental conditions be carefully controlled during laser interferometer measurements, and what is the approximate error contribution of a 1C temperature change?',
		'List the four layers of a modern precision motion control system hierarchy from top to bottom, and describe the primary function of each layer.',
		'Compare trapezoidal and S-curve motion profiles. Why does the S-curve profile produce less residual vibration despite having a longer move time?',
		'Why does a servo drive use a cascaded (nested) three-loop control architecture instead of a single position control loop?',
		"Explain EtherCAT's unique on-the-fly data processing principle and how its Distributed Clock mechanism achieves sub-microsecond synchronization.",
		'Describe the Ziegler-Nichols tuning method and explain why the resulting gains are typically used only as a starting point in servo applications.',
		'Explain why mechanical resonances limit servo bandwidth, and describe how a notch filter restores gain margin at the resonance frequency.',
		'What are the three types of feedforward control used in motion systems, and what does each compensate for?',
		'What is the steady-state following error formula for a proportional-only position loop during constant velocity, and what are the two approaches to reduce it?',
		'What is Iterative Learning Control (ILC), and what is its key limitation?',
		'Name the five levels of the Purdue Reference Model and identify which level servo drives and PLCs belong to.',
		"What makes OPC-UA's information model fundamentally different from simply transporting raw data values? Explain the concept of semantic interoperability.",
		'List four key failure modes in direct drive motion systems and the observable signals used to detect each.',
		'What are the four IEC 62443 Security Levels, and what is the typical minimum target for a semiconductor fab environment?',
		'In a high-speed semiconductor die bonding machine, explain why different motor technologies (ironless linear motors, VCMs, and DDR motors) are each selected for different axes, and how the control system coordinates them.',
		'Why is unsupervised anomaly detection preferred over supervised RUL prediction for predictive maintenance of expensive precision motion equipment?',
		'Describe the practical DMZ architecture for securely sharing data between an OT control network and the IT corporate network. What is the role of a unidirectional data diode?',
		'Describe the four stages of rolling element bearing degradation according to ISO 17359, and at which stage should predictive maintenance trigger a maintenance action?',
		'How are machine learning models deployed at the edge in industrial motion control systems, and why is edge deployment preferred over cloud-based inference?',
		'What is Cosine Error, and how does it compare to Abbe Error in terms of growth behavior? Calculate the Cosine Error for a 1 degree misalignment across 1 m of travel.',
		'What are the key advantages and disadvantages of air bearings compared to rolling element bearings in precision stages?',
		'What is Cyclic Synchronous Position (CSP) mode in the CiA 402 device profile, and why is it the standard for precision multi-axis motion control?',
		'What is a Disturbance Observer (DOB), and how does it improve servo performance without increasing outer loop gains?',
		'How does Wiegand wire technology enable battery-free multi-turn absolute position tracking in encoders?'
	];

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

	function getQuestionsForSelectedAgent(model: SelectedModel): SuggestionQuestion[] {
		const agentKey = getSelectedAgentKey(model);

		if (agentKey === 'silicore') {
			return SEMICONDUCTOR_QUESTIONS.map((question) => ({
				content: question,
				category: 'Semiconductor'
			}));
		}

		if (agentKey === 'kinetix') {
			return KINETIX_QUESTIONS.map((question) => ({
				content: question,
				category: 'Kinetix'
			}));
		}

		if (agentKey === 'meeting-room-agent') {
			return [];
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

		return '';
	}

	let displayedQuestions: SuggestionQuestion[] = [];

	$: displayedQuestions =
		inputValue.trim().length > 0
			? []
			: shuffle(getQuestionsForSelectedAgent(selectedModel)).slice(0, 4);
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
