// Backend base URL. Override with VITE_API_BASE in frontend/.env if needed.
// Trailing slashes are stripped so "https://host/" and "https://host" behave the same.
export const API_BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/+$/, '');

export const MAX_UPLOAD_MB = 50;
