import axios from 'axios';

export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`, withCredentials: true });
let csrfToken = null;
export const setCsrfToken = value => { csrfToken = value; };
api.interceptors.request.use(config => {
  if (csrfToken && !['get', 'head', 'options'].includes(config.method?.toLowerCase())) config.headers['X-CSRF-Token'] = csrfToken;
  return config;
});
export const errorText = e => typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.response?.data?.detail?.message || 'Something went wrong. Please try again.';
export const short = (value = '') => value.length > 16 ? `${value.slice(0, 5)}…${value.slice(-5)}` : value;
export const explorer = signature => `https://explorer.solana.com/tx/${encodeURIComponent(signature)}?cluster=devnet`;
