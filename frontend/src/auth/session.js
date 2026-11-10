import { reactive } from "vue";
export const session = reactive({
  token: sessionStorage.getItem("access_token") || "",
  user: null,
});
export function setToken(token) {
  session.token = token;
  session.user = null;
  sessionStorage.setItem("access_token", token);
}
export function clearSession() {
  session.token = "";
  session.user = null;
  sessionStorage.removeItem("access_token");
}
