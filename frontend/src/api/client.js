import axios from "axios";
import { session, clearSession } from "../auth/session";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
});
let unauthorized = () => {};
export function onUnauthorized(handler) {
  unauthorized = handler;
}
api.interceptors.request.use((config) => {
  if (!import.meta.env.VITE_API_BASE_URL)
    throw new Error("未配置 API 服务地址");
  if (session.token && config.url !== "/api/auth/login")
    config.headers.Authorization = `Bearer ${session.token}`;
  return config;
});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // 旧会话的延迟响应不能清除新登录的会话。
    if (
      error.response?.status === 401 &&
      error.config?.url !== "/api/auth/login" &&
      error.config?.headers?.Authorization === `Bearer ${session.token}`
    ) {
      clearSession();
      unauthorized();
    }
    return Promise.reject(error);
  },
);
export async function loadUser() {
  const token = session.token;
  const { data } = await api.get("/api/me");
  if (session.token !== token) throw new Error("会话已变更");
  if (!["admin", "member"].includes(data.role)) {
    clearSession();
    throw new Error("角色无效");
  }
  session.user = data;
  return data;
}
