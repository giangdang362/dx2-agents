import { WEBUI_API_BASE_URL } from '$lib/constants';

const MEETING_API_BASE = `${WEBUI_API_BASE_URL}/meeting-rooms`;

export const listRooms = async (token: string = '') => {
	const res = await fetch(`${MEETING_API_BASE}/rooms`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listAdmins = async (token: string = '') => {
	const res = await fetch(`${MEETING_API_BASE}/admins`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listDepartments = async (token: string = '') => {
	const res = await fetch(`${MEETING_API_BASE}/departments`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listCateringOptions = async (token: string = '') => {
	const res = await fetch(`${MEETING_API_BASE}/catering-options`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const listBookings = async (token: string = '') => {
	const res = await fetch(`${MEETING_API_BASE}/bookings`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getBooking = async (token: string = '', bookingId: string) => {
	const res = await fetch(`${MEETING_API_BASE}/bookings/${bookingId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const saveBooking = async (token: string = '', booking: object) => {
	const res = await fetch(`${MEETING_API_BASE}/bookings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(booking)
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const patchBooking = async (
	token: string = '',
	bookingId: string,
	data: { status?: string; admin_note?: string }
) => {
	const res = await fetch(`${MEETING_API_BASE}/bookings/${bookingId}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(data)
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const deleteBooking = async (token: string = '', bookingId: string) => {
	const res = await fetch(`${MEETING_API_BASE}/bookings/${bookingId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const checkAvailability = async (
	token: string = '',
	params: { date: string; start_time: string; end_time: string; exclude_id?: string }
) => {
	const searchParams = new URLSearchParams({
		date: params.date,
		start_time: params.start_time,
		end_time: params.end_time
	});
	if (params.exclude_id) {
		searchParams.append('exclude_id', params.exclude_id);
	}
	const res = await fetch(`${MEETING_API_BASE}/availability?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};
