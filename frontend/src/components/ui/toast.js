import { reactive, shallowRef } from "vue";
export const notices = reactive([]);
let sequence = 0;
export function toast(message, type = "success") {
  const id = ++sequence;
  notices.push({ id, message, type });
  if (notices.length > 4) notices.shift();
  setTimeout(() => dismiss(id), 6000);
}
export function dismiss(id) {
  const index = notices.findIndex((item) => item.id === id);
  if (index >= 0) notices.splice(index, 1);
}
export function errorMessage(error, fallback = "操作失败，请稍后重试") {
  const detail = error.response?.data?.detail;
  if (error.response?.status === 403) return "没有权限执行此操作";
  return typeof detail === "string" ? detail : fallback;
}

export const toastTarget = shallowRef(null);
