import { beforeEach, describe, expect, it, vi } from "vitest";

vi.hoisted(() => {
  const values = new Map();
  vi.stubGlobal("sessionStorage", {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  });
});
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, createWebHistory: actual.createMemoryHistory };
});
import { api, loadUser } from "../src/api/client";
import { session, setToken, clearSession } from "../src/auth/session";
import { router } from "../src/router";

beforeEach(async () => {
  vi.restoreAllMocks();
  vi.stubEnv("VITE_API_BASE_URL", "https://test.invalid");
  clearSession();
  await router.push("/login");
});

describe("登录会话与权限导航", () => {
  it("未登录访问受保护页面跳回登录", async () => {
    await router.push("/admin/settings");
    expect(router.currentRoute.value.path).toBe("/login");
  });
  it.each(["admin", "member"])(
    "从 me 获取 %s 角色并进入对应首页",
    async (role) => {
      setToken("test-token");
      vi.spyOn(api, "get").mockResolvedValue({
        data: { id: 1, username: role, role },
      });
      await router.push("/");
      expect(api.get).toHaveBeenCalledWith("/api/me");
      expect(router.currentRoute.value.path).toBe(`/${role}/dashboard`);
    },
  );
  it("成员不能访问管理页，允许成员评分页", async () => {
    setToken("test-token");
    session.user = { role: "member" };
    await router.push("/admin/settings");
    expect(router.currentRoute.value.path).toBe("/member/dashboard");
    await router.push("/member/scores");
    expect(router.currentRoute.value.path).toBe("/member/scores");
  });
  it("管理员可以切换设置页和评分页", async () => {
    setToken("test-token");
    session.user = { role: "admin" };
    for (const path of ["/admin/settings", "/admin/scores"]) {
      await router.push(path);
      expect(router.currentRoute.value.path).toBe(path);
    }
  });
  it("无效 token 的用户校验失败后清除会话", async () => {
    setToken("test-token");
    vi.spyOn(api, "get").mockRejectedValue(new Error("401"));
    await router.push("/member/dashboard");
    expect(session.token).toBe("");
    expect(router.currentRoute.value.path).toBe("/login");
  });
  it("旧会话的 me 响应不能覆盖新会话", async () => {
    setToken("old-token");
    let resolve;
    vi.spyOn(api, "get").mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const pending = loadUser();
    setToken("new-token");
    resolve({ data: { role: "admin" } });
    await expect(pending).rejects.toThrow("会话已变更");
    expect(session.user).toBeNull();
  });
});

describe("请求拦截器", () => {
  it("业务请求携带 Bearer，登录请求不携带旧 token", async () => {
    setToken("test-token");
    const headers = [];
    const adapter = async (config) => {
      headers.push(config.headers.Authorization);
      return { data: {}, status: 200, statusText: "OK", headers: {}, config };
    };
    await api.get("/api/me", { adapter });
    await api.post("/api/auth/login", {}, { adapter });
    expect(headers).toEqual(["Bearer test-token", undefined]);
  });
  it("当前请求 401 清除会话", async () => {
    setToken("test-token");
    session.user = { role: "admin" };
    await router.push("/admin/dashboard");
    await expect(
      api.get("/api/me", {
        adapter: async (config) => {
          throw { response: { status: 401 }, config };
        },
      }),
    ).rejects.toBeTruthy();
    expect(session.token).toBe("");
    await vi.waitFor(() =>
      expect(router.currentRoute.value.path).toBe("/login"),
    );
  });
  it("旧请求延迟 401 不清除新会话", async () => {
    setToken("old-token");
    await expect(
      api.get("/api/me", {
        adapter: async (config) => {
          setToken("new-token");
          throw { response: { status: 401 }, config };
        },
      }),
    ).rejects.toBeTruthy();
    expect(session.token).toBe("new-token");
  });
});
