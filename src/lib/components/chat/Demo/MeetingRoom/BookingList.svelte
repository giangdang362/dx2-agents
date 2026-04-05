<script lang="ts">
	import { fly } from 'svelte/transition';

	export let bookings: any[] = [];

	const STATUS_CONFIG = {
		draft:     { label: 'Pending Confirmation', color: '#6366f1' },
		pending:   { label: 'Pending Approval',    color: '#f59e0b' },
		approved:  { label: 'Approved',     color: '#10b981' },
		rejected:  { label: 'Rejected',      color: '#ef4444' },
		cancelled: { label: 'Cancelled',       color: '#6b7280' },
		sent:      { label: 'Sent',       color: '#3b82f6' }
	};

	const LOCATION_NAMES = { HN: 'Hanoi', HCM: 'Ho Chi Minh City', DN: 'Da Nang' };
	const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

	function formatDate(dateStr: string) {
		if (!dateStr) return '—';
		try {
			const [y, m, d] = dateStr.split('-');
			const dow = DAY_NAMES[new Date(dateStr).getDay()];
			return `${dow}, ${d}/${m}/${y}`;
		} catch {
			return dateStr;
		}
	}

	function locationDisplay(b: any) {
		const city = (LOCATION_NAMES as any)[b.location] || b.location || '—';
		return b.room_name ? `${city} / ${b.room_name}` : city;
	}

	function clientDisplay(b: any) {
		return b.client?.trim() || 'Internal';
	}

	function getStatus(b: any) {
		return (STATUS_CONFIG as any)[b.status] ?? STATUS_CONFIG.pending;
	}

	function cateringDisplay(b: any) {
		if (!b.catering || (Array.isArray(b.catering?.items) && b.catering.items.length === 0)) {
			return null;
		}
		if (typeof b.catering === 'object' && b.catering.items?.length) {
			return `${b.catering.items.length} item(s)`;
		}
		return null;
	}
</script>

<div class="booking-list-card" in:fly={{ y: 20, duration: 400 }}>
	<!-- Header -->
	<div class="list-header">
		<div class="header-left">
			<svg class="header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
				<line x1="16" y1="2" x2="16" y2="6"></line>
				<line x1="8" y1="2" x2="8" y2="6"></line>
				<line x1="3" y1="10" x2="21" y2="10"></line>
			</svg>
			<div>
				<div class="header-label">CMC GLOBAL</div>
				<div class="header-title">Your Meeting Schedule</div>
			</div>
		</div>
		<div class="header-count">{bookings.length} meeting(s)</div>
	</div>

	<!-- Body -->
	<div class="list-body">
		{#if bookings.length === 0}
			<div class="empty-state">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
					<rect x="3" y="4" width="18" height="18" rx="2"></rect>
					<line x1="16" y1="2" x2="16" y2="6"></line>
					<line x1="8" y1="2" x2="8" y2="6"></line>
					<line x1="3" y1="10" x2="21" y2="10"></line>
				</svg>
				<p>No upcoming meetings.</p>
			</div>
		{:else}
			{#each bookings as booking, i}
				{@const status = getStatus(booking)}
				<div
					class="booking-row"
					style="--accent: {status.color}"
					in:fly={{ y: 10, duration: 250, delay: i * 60 }}
				>
					<div class="accent-bar"></div>
					<div class="row-content">
						<div class="row-top">
							<span class="client-name">{clientDisplay(booking)}</span>
							<span class="status-badge" style="background: {status.color}20; color: {status.color}; border-color: {status.color}40">
								{status.label}
							</span>
						</div>
						<div class="row-meta">
							<div class="meta-item">
								<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
									<line x1="16" y1="2" x2="16" y2="6"></line>
									<line x1="8" y1="2" x2="8" y2="6"></line>
									<line x1="3" y1="10" x2="21" y2="10"></line>
								</svg>
								<span>{formatDate(booking.date)}</span>
							</div>
							<div class="meta-item">
								<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<circle cx="12" cy="12" r="10"></circle>
									<polyline points="12 6 12 12 16 14"></polyline>
								</svg>
								<span>{booking.start_time || '—'} – {booking.end_time || '—'}</span>
							</div>
							<div class="meta-item">
								<svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"></path>
									<circle cx="12" cy="10" r="3"></circle>
								</svg>
								<span>{locationDisplay(booking)}</span>
							</div>
							<div class="meta-item">
								<span class="catering-indicator {cateringDisplay(booking) ? 'has-catering' : 'no-catering'}">
									{cateringDisplay(booking) ? `☕ ${cateringDisplay(booking)}` : '☕ None'}
								</span>
							</div>
						</div>
						{#if booking.title}
							<div class="booking-title">{booking.title}</div>
						{/if}
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	.booking-list-card {
		background: linear-gradient(145deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.95) 100%);
		backdrop-filter: blur(20px);
		border: 1px solid rgba(226, 232, 240, 0.8);
		border-radius: 20px;
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.02),
			0 10px 15px -3px rgba(0, 0, 0, 0.04),
			0 25px 50px -12px rgba(0, 0, 0, 0.08);
		width: 100%;
		max-width: 100%;
		overflow: hidden;
		font-family: 'Century Gothic', 'Trebuchet MS', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
	}

	/* ── Header ── */
	.list-header {
		background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #6366f1 100%);
		padding: 18px 24px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		position: relative;
		overflow: hidden;
	}
	:global(.dark) .list-header {
		background: linear-gradient(135deg, #1e293b 0%, #1e3a5f 50%, #2e1065 100%);
	}

	.list-header::before {
		content: '';
		position: absolute;
		top: -50%;
		right: -10%;
		width: 160px;
		height: 160px;
		background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, transparent 70%);
		border-radius: 50%;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 12px;
		position: relative;
		z-index: 1;
	}

	.header-icon {
		width: 28px;
		height: 28px;
		color: rgba(255, 255, 255, 0.85);
		flex-shrink: 0;
	}

	.header-label {
		font-size: 10px;
		font-weight: 700;
		color: rgba(255, 255, 255, 0.6);
		letter-spacing: 1.5px;
		text-transform: uppercase;
		margin-bottom: 2px;
	}

	.header-title {
		font-size: 17px;
		font-weight: 700;
		color: white;
		letter-spacing: 0.2px;
	}

	.header-count {
		font-size: 12px;
		font-weight: 600;
		color: rgba(255, 255, 255, 0.75);
		background: rgba(255, 255, 255, 0.15);
		padding: 4px 12px;
		border-radius: 20px;
		position: relative;
		z-index: 1;
	}

	/* ── Body ── */
	.list-body {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	/* ── Empty state ── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		padding: 32px 20px;
		color: #94a3b8;
	}

	.empty-state svg {
		opacity: 0.4;
	}

	.empty-state p {
		font-size: 13px;
		color: #94a3b8;
		margin: 0;
	}

	/* ── Booking row ── */
	.booking-row {
		display: flex;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 12px;
		overflow: hidden;
		transition: box-shadow 0.2s, transform 0.2s;
	}

	.booking-row:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
		transform: translateY(-1px);
	}

	.accent-bar {
		width: 4px;
		min-width: 4px;
		background: var(--accent, #6366f1);
		border-radius: 0;
		flex-shrink: 0;
	}

	.row-content {
		flex: 1;
		padding: 12px 14px;
		min-width: 0;
	}

	/* ── Row top: client + badge ── */
	.row-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 8px;
	}

	.client-name {
		font-size: 13px;
		font-weight: 700;
		color: #1e293b;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.status-badge {
		font-size: 10px;
		font-weight: 600;
		padding: 3px 9px;
		border-radius: 20px;
		border: 1px solid;
		white-space: nowrap;
		flex-shrink: 0;
	}

	/* ── Meta row ── */
	.row-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 10px 16px;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 12px;
		color: #475569;
	}

	.meta-icon {
		width: 13px;
		height: 13px;
		color: #94a3b8;
		flex-shrink: 0;
	}

	/* ── Catering indicator ── */
	.catering-indicator {
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 10px;
	}

	.catering-indicator.has-catering {
		color: #92400e;
		background: #fef3c7;
	}

	.catering-indicator.no-catering {
		color: #6b7280;
		background: #f3f4f6;
	}

	/* ── Optional title ── */
	.booking-title {
		margin-top: 6px;
		font-size: 11px;
		color: #94a3b8;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* ══════════════════════════════════════
	   Dark mode overrides
	   ══════════════════════════════════════ */

	:global(.dark) .booking-list-card {
		background: linear-gradient(145deg, rgba(30, 41, 59, 0.97) 0%, rgba(15, 23, 42, 0.97) 100%);
		border-color: rgba(51, 65, 85, 0.8);
		box-shadow:
			0 4px 6px -1px rgba(0, 0, 0, 0.2),
			0 10px 15px -3px rgba(0, 0, 0, 0.3),
			0 25px 50px -12px rgba(0, 0, 0, 0.5);
	}

	/* Header gradient is unchanged — it already reads well on dark backgrounds */

	:global(.dark) .empty-state {
		color: #94a3b8;
	}

	:global(.dark) .empty-state p {
		color: #94a3b8;
	}

	:global(.dark) .booking-row {
		background: #1e293b;
		border-color: #334155;
	}

	:global(.dark) .booking-row:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	:global(.dark) .client-name {
		color: #f1f5f9;
	}

	:global(.dark) .meta-item {
		color: #94a3b8;
	}

	:global(.dark) .meta-icon {
		color: #475569;
	}

	:global(.dark) .catering-indicator.has-catering {
		color: #fde68a;
		background: rgba(146, 64, 14, 0.35);
	}

	:global(.dark) .catering-indicator.no-catering {
		color: #94a3b8;
		background: rgba(51, 65, 85, 0.6);
	}

	:global(.dark) .booking-title {
		color: #475569;
	}
</style>
