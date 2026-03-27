<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		updateUserTimezone
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, getUserTimezone } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	let authing = false;

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			// Update user timezone
			const timezone = getUserTimezone();
			if (sessionUser.token && timezone) {
				updateUserTimezone(sessionUser.token, timezone);
			}

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			// Chờ routing hoàn tất rồi mới hiển thị thông báo
			await goto(redirectPath);
			toast.success($i18n.t(`You're now logged in.`));
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		authing = true;
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
		authing = false;
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<!-- Auth Page Root -->
<div class="auth-root" id="auth-page">
	<!-- Drag region for desktop apps -->
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region" />

	<!-- Animated grid overlay -->
	<div class="grid-overlay" aria-hidden="true"></div>

	<!-- Subtle radial glow -->
	<div class="radial-glow" aria-hidden="true"></div>

	{#if loaded}
		{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
			<div class="flex items-center justify-center min-h-screen">
				<div class="flex items-center gap-3 text-xl text-white/70">
					<span>{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}</span>
					<Spinner className="size-5" />
				</div>
			</div>
		{:else}
			<div class="auth-center" id="auth-container">
				<!-- Logo -->
				<div class="logo-wrap">
					<img src="/src/routes/auth/logo.svg" alt="CMC Global Logo" class="auth-logo" />
				</div>

				<!-- Card -->
				<div class="auth-card">
					<!-- Greeting inside card -->
					{#if mode === 'signin'}
						<div class="card-greeting">
							<p class="auth-welcome">Welcome back!</p>
							<p class="auth-sub">Sign in to your account to continue</p>
						</div>
					{:else if mode === 'signup'}
						<div class="card-greeting">
							<p class="auth-welcome">Create account</p>
							<p class="auth-sub">Join {$WEBUI_NAME} today</p>
						</div>
					{:else}
						<div class="card-greeting">
							<p class="auth-welcome">LDAP Sign In</p>
							<p class="auth-sub">Authenticate with your organisation</p>
						</div>
					{/if}

					{#if $config?.metadata?.auth_logo_position === 'center'}
						<div class="flex justify-center mb-5">
							<img
								id="logo"
								crossorigin="anonymous"
								src="{WEBUI_BASE_URL}/static/cmc-logo-loading.png"
								class="size-16 rounded-full ring-2 ring-white/10"
								alt="{$WEBUI_NAME} logo"
							/>
						</div>
					{/if}

					<form
						class="flex flex-col gap-4"
						on:submit={(e) => {
							e.preventDefault();
							submitHandler();
						}}
					>
						<!-- Onboarding notice -->
						{#if $config?.onboarding ?? false}
							<div class="auth-notice">
								ⓘ {$WEBUI_NAME}
								{$i18n.t(
									'does not make any external connections, and your data stays securely on your locally hosted server.'
								)}
							</div>
						{/if}

						{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
							<!-- Name (signup) -->
							{#if mode === 'signup'}
								<div class="field-group">
									<label for="name" class="field-label">{$i18n.t('Name')}</label>
									<input
										bind:value={name}
										type="text"
										id="name"
										class="field-input"
										autocomplete="name"
										placeholder={$i18n.t('Enter Your Full Name')}
										required
									/>
								</div>
							{/if}

							<!-- LDAP username -->
							{#if mode === 'ldap'}
								<div class="field-group">
									<label for="username" class="field-label">{$i18n.t('Username')}</label>
									<input
										bind:value={ldapUsername}
										type="text"
										class="field-input"
										autocomplete="username"
										name="username"
										id="username"
										placeholder={$i18n.t('Enter Your Username')}
										required
									/>
								</div>
							{:else}
								<!-- Email -->
								<div class="field-group">
									<label for="email" class="field-label">{$i18n.t('Email')}</label>
									<input
										bind:value={email}
										type="email"
										id="email"
										class="field-input"
										autocomplete="email"
										name="email"
										placeholder={$i18n.t('Enter Your Email')}
										required
									/>
								</div>
							{/if}

							<!-- Password -->
							<div class="field-group">
								<label for="password" class="field-label">{$i18n.t('Password')}</label>
								<div class="field-input field-input--password">
									<SensitiveInput
										bind:value={password}
										type="password"
										id="password"
										outerClassName="flex flex-1 bg-transparent"
										inputClassName="w-full text-sm bg-transparent text-[#e8edf5] placeholder-white/25 outline-none"
										showButtonClassName="text-white/35 hover:text-white/70 transition bg-transparent flex-shrink-0"
										placeholder={$i18n.t('Enter Your Password')}
										autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
										screenReader={true}
										required
									/>
								</div>
							</div>

							<!-- Confirm Password (signup) -->
							{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
								<div class="field-group">
									<label for="confirm-password" class="field-label"
										>{$i18n.t('Confirm Password')}</label
									>
									<div class="field-input field-input--password">
										<SensitiveInput
											bind:value={confirmPassword}
											type="password"
											id="confirm-password"
											outerClassName="flex flex-1 bg-transparent"
											inputClassName="w-full text-sm bg-transparent text-[#e8edf5] placeholder-white/25 outline-none"
											showButtonClassName="text-white/35 hover:text-white/70 transition bg-transparent flex-shrink-0"
											placeholder={$i18n.t('Confirm Your Password')}
											autocomplete="new-password"
											required
										/>
									</div>
								</div>
							{/if}

							<button
								type="submit"
								class="btn-primary flex justify-center items-center gap-2"
								disabled={authing}
							>
								<span>
									{#if mode === 'ldap'}
										{$i18n.t('Authenticate')}
									{:else if mode === 'signin'}
										{$i18n.t('Sign in')}
									{:else if $config?.onboarding ?? false}
										{$i18n.t('Create Admin Account')}
									{:else}
										{$i18n.t('Create Account')}
									{/if}
								</span>
								{#if authing}
									<Spinner className="size-4" />
								{/if}
							</button>
						{/if}

						<!-- OAuth providers -->
						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="divider-or">
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<span class="divider-label">{$i18n.t('or')}</span>
								{/if}
							</div>
							<div class="flex flex-col gap-2">
								{#if $config?.oauth?.providers?.google}
									<button
										type="button"
										class="btn-oauth"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 48 48"
											class="size-5"
											aria-hidden="true"
										>
											<path
												fill="#EA4335"
												d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
											/><path
												fill="#4285F4"
												d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
											/><path
												fill="#FBBC05"
												d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
											/><path
												fill="#34A853"
												d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
											/><path fill="none" d="M0 0h48v48H0z" />
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										type="button"
										class="btn-oauth"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 21 21"
											class="size-5"
											aria-hidden="true"
										>
											<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
												x="1"
												y="11"
												width="9"
												height="9"
												fill="#00a4ef"
											/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
												x="11"
												y="11"
												width="9"
												height="9"
												fill="#ffb900"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										type="button"
										class="btn-oauth"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 24 24"
											class="size-5"
											aria-hidden="true"
										>
											<path
												fill="currentColor"
												d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										type="button"
										class="btn-oauth"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-5"
											aria-hidden="true"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>
										<span
											>{$i18n.t('Continue with {{provider}}', {
												provider: $config?.oauth?.providers?.oidc ?? 'SSO'
											})}</span
										>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.feishu}
									<button
										type="button"
										class="btn-oauth"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
										}}
									>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
									</button>
								{/if}
							</div>
						{/if}

						<!-- LDAP toggle -->
						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="text-center mt-1">
								<button
									class="text-xs text-white/40 hover:text-white/70 underline underline-offset-2 transition"
									type="button"
									on:click={() => {
										if (mode === 'ldap')
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										else mode = 'ldap';
									}}
								>
									{mode === 'ldap' ? $i18n.t('Continue with Email') : $i18n.t('Continue with LDAP')}
								</button>
							</div>
						{/if}

						<!-- Signup / Signin toggle -->
						{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
							{#if mode !== 'ldap'}
								<p class="text-center text-sm text-white/40 mt-1">
									{mode === 'signin'
										? $i18n.t("Don't have an account?")
										: $i18n.t('Already have an account?')}
									<button
										class="text-white/70 font-medium underline underline-offset-2 hover:text-white transition ml-1"
										type="button"
										on:click={() => {
											mode = mode === 'signin' ? 'signup' : 'signin';
										}}
									>
										{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
									</button>
								</p>
							{/if}
						{/if}
					</form>

					<!-- Footer -->
					{#if $config?.metadata?.login_footer}
						<div class="mt-5 text-[0.68rem] text-white/25 text-center leading-relaxed">
							{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
						</div>
					{/if}
				</div>
			</div>
		{/if}
	{/if}
</div>

<style>
	/* ── Root ── */
	.auth-root {
		position: relative;
		width: 100%;
		min-height: 100dvh;
		overflow: hidden;
		background: linear-gradient(135deg, #0b0f1a 0%, #0d1425 40%, #0f1c2e 70%, #0b0f1a 100%);
		font-family: 'Inter', system-ui, sans-serif;
	}

	/* ── Grid overlay ── */
	.grid-overlay {
		position: absolute;
		inset: 0;
		pointer-events: none;
		opacity: 0.035;
		background-image: linear-gradient(rgba(255, 255, 255, 0.18) 1px, transparent 1px),
			linear-gradient(90deg, rgba(255, 255, 255, 0.18) 1px, transparent 1px);
		background-size: 48px 48px;
		/* Fade the grid out at edges for a softer look */
		-webkit-mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
		mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 40%, transparent 100%);
	}

	/* ── Radial glow ── */
	.radial-glow {
		position: absolute;
		inset: 0;
		pointer-events: none;
		background: radial-gradient(
			ellipse 70% 60% at 50% 30%,
			rgba(0, 143, 213, 0.07) 0%,
			transparent 70%
		);
	}

	/* ── Center layout ── */
	.auth-center {
		position: relative;
		z-index: 10;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100dvh;
		padding: 2rem 1rem;
	}

	/* ── Logo ── */
	.logo-wrap {
		margin-bottom: 2rem;
	}
	.auth-logo {
		height: 80px;
		width: auto;
		/* Make the blue SVG paths appear in a softer blue-white on the dark bg */
		filter: brightness(1.15) saturate(0.85);
		opacity: 0.9;
	}

	/* ── Greeting (inside card) ── */
	.card-greeting {
		margin-bottom: 1.5rem;
		padding-bottom: 1.25rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}
	.auth-welcome {
		font-size: 1.3rem;
		font-weight: 700;
		color: #e8edf5;
		letter-spacing: -0.02em;
		margin: 0 0 0.2rem;
		text-align: left;
	}
	.auth-sub {
		font-size: 0.8rem;
		color: rgba(255, 255, 255, 0.38);
		margin: 0;
		text-align: left;
	}

	/* ── Card ── */
	.auth-card {
		width: 100%;
		max-width: 480px;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.07);
		border-radius: 16px;
		padding: 2rem 2.25rem;
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		box-shadow:
			0 0 0 1px rgba(0, 143, 213, 0.06) inset,
			0 24px 64px rgba(0, 0, 0, 0.5);
	}

	/* ── Notice ── */
	.auth-notice {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.35);
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.06);
		border-radius: 8px;
		padding: 0.625rem 0.875rem;
		line-height: 1.5;
	}

	/* ── Fields ── */
	.field-group {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}
	.field-label {
		font-size: 0.8rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.5);
		letter-spacing: 0.01em;
	}
	:global(.field-input),
	.field-input {
		width: 100%;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.09);
		border-radius: 8px;
		padding: 0.625rem 0.875rem;
		font-size: 0.875rem;
		color: #e8edf5;
		caret-color: #e8edf5;
		outline: none;
		transition:
			border-color 0.2s,
			box-shadow 0.2s;
	}
	:global(.field-input::placeholder),
	.field-input::placeholder {
		color: rgba(255, 255, 255, 0.22);
	}
	:global(.field-input:-webkit-autofill),
	:global(.field-input:-webkit-autofill:hover),
	:global(.field-input:-webkit-autofill:focus),
	:global(.field-input:-webkit-autofill:active),
	.field-input:-webkit-autofill,
	.field-input:-webkit-autofill:hover,
	.field-input:-webkit-autofill:focus,
	.field-input:-webkit-autofill:active {
		/* Thay đổi màu chữ và nền của Autofill cho hợp với Dark Mode */
		-webkit-text-fill-color: #e8edf5 !important;
		-webkit-box-shadow: 0 0 0px 1000px #1e293b inset !important;
		transition: background-color 5000s ease-in-out 0s;
		border-radius: 8px;
	}

	/* Focus state cho cả email input và password wrapper */
	:global(.field-input:focus),
	:global(.field-input:focus-within),
	.field-input:focus,
	.field-input:focus-within {
		border-color: rgba(0, 143, 213, 0.6);
		/* box-shadow:
			0 0 0 4px rgba(0, 143, 213, 0.2),
			0 0 12px rgba(0, 143, 213, 0.3) !important; */
	}

	/* Password wrapper — khớp hoàn toàn với email input */
	.field-input--password {
		display: flex;
		align-items: stretch;
		padding: 0;
		overflow: hidden; /* Fix mất góc bo khi autofill fill background vuông */
	}
	:global(.field-input--password > div) {
		display: flex;
		flex: 1;
		align-items: center;
	}
	:global(.field-input--password input) {
		flex: 1;
		padding: 0.625rem 0 0.625rem 0.875rem;
		font-size: 0.875rem;
		color: #e8edf5;
		caret-color: #e8edf5;
		background: transparent;
		border: none;
		outline: none;
		min-width: 0;
		width: 100%;
		border-radius: 8px 0 0 8px; /* Giữ bo góc bên trái để tránh autofill đè */
	}
	:global(.field-input--password input:-webkit-autofill),
	:global(.field-input--password input:-webkit-autofill:hover),
	:global(.field-input--password input:-webkit-autofill:focus) {
		-webkit-text-fill-color: #e8edf5 !important;
		-webkit-box-shadow: 0 0 0px 1000px #1e293b inset !important;
		transition: background-color 5000s ease-in-out 0s;
	}
	:global(.field-input--password input::placeholder) {
		color: rgba(255, 255, 255, 0.22);
	}
	:global(.field-input--password button) {
		padding: 0.625rem 0.875rem;
		color: rgba(255, 255, 255, 0.35);
		background: transparent;
		border: none;
		flex-shrink: 0;
		cursor: pointer;
		display: flex;
		align-items: center;
		transition: color 0.2s;
	}
	:global(.field-input--password button:hover) {
		color: rgba(255, 255, 255, 0.75);
	}
	/* Bỏ shadow mặc định của trình duyệt để shadow tùy chỉnh hoạt động tốt nhất */
	:global(.field-input--password input:focus) {
		outline: none;
		box-shadow: none;
	}

	/* ── Primary button ── */
	.btn-primary {
		width: 100%;
		padding: 0.7rem 1rem;
		border-radius: 8px;
		font-size: 0.9rem;
		font-weight: 600;
		color: #fff;
		background: linear-gradient(135deg, #0072b5 0%, #0094d6 100%);
		border: none;
		cursor: pointer;
		transition:
			opacity 0.2s,
			box-shadow 0.2s,
			transform 0.15s;
		box-shadow: 0 4px 16px rgba(0, 143, 213, 0.25);
		margin-top: 0.25rem;
	}
	.btn-primary:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}
	.btn-primary:not(:disabled):hover {
		opacity: 0.9;
		box-shadow: 0 6px 22px rgba(0, 143, 213, 0.35);
		transform: translateY(-0.25px);
	}
	.btn-primary:not(:disabled):active {
		transform: translateY(0);
	}

	/* ── OAuth buttons ── */
	.btn-oauth {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.625rem;
		width: 100%;
		padding: 0.6rem 1rem;
		border-radius: 8px;
		font-size: 0.875rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.7);
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.08);
		cursor: pointer;
		transition:
			background 0.2s,
			color 0.2s,
			border-color 0.2s;
	}
	.btn-oauth:hover {
		background: rgba(255, 255, 255, 0.08);
		color: #fff;
		border-color: rgba(255, 255, 255, 0.14);
	}

	/* ── Divider ── */
	.divider-or {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}
	.divider-or::before,
	.divider-or::after {
		content: '';
		flex: 1;
		height: 1px;
		background: rgba(255, 255, 255, 0.07);
	}
	.divider-label {
		font-size: 0.75rem;
		color: rgba(255, 255, 255, 0.3);
		flex-shrink: 0;
	}
</style>
