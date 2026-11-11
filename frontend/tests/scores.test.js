import { beforeEach, describe, expect, it, vi } from "vitest";
vi.hoisted(() => {
  vi.stubGlobal("sessionStorage", {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {},
  });
});
import { api } from "../src/api/client";
import { fetchScores, projectScore, percent } from "../src/api/scores";
import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import JsonViewer from "../src/components/ui/JsonViewer.vue";
import AppPagination from "../src/components/ui/AppPagination.vue";
beforeEach(() => vi.restoreAllMocks());
describe("评分权限与展示", () => {
  it("成员数据白名单剔除计算细节、原始包和未知字段", () => {
    const row = projectScore(
      {
        id: 1,
        total_score: 0,
        score_detail: { secret: 1 },
        raw_payload: { secret: 2 },
        algorithm_configs: { secret: 3 },
      },
      false,
    );
    expect(row.total_score).toBe(0);
    expect(row).not.toHaveProperty("score_detail");
    expect(row).not.toHaveProperty("raw_payload");
    expect(row).not.toHaveProperty("algorithm_configs");
  });
  it.each([false, true])("按管理员状态 %s 选择正确接口", async (admin) => {
    const get = vi.spyOn(api, "get").mockResolvedValue({
      data: {
        items: [{ id: 1, score_detail: { x: 1 }, raw_payload: { a: 2 } }],
        total: 1,
      },
    });
    const params = {
      page: 2,
      page_size: 10,
      up_name: "UP",
      date_from: "2026-01-01",
      director: "编导",
    };
    const result = await fetchScores(admin, params);
    expect(get).toHaveBeenCalledWith(
      admin ? "/api/admin/scores" : "/api/member/scores",
      { params, signal: undefined, paramsSerializer: { indexes: null } },
    );
    expect("score_detail" in result.items[0]).toBe(admin);
  });
  it("百分比区分零和缺失", () => {
    expect(percent(0)).toBe("0.00%");
    expect(percent(null)).toBe("—");
    expect(percent(0.25)).toBe("25.00%");
  });
  it("JSON 使用文本转义防止原始字段执行 HTML", async () => {
    const html = await renderToString(
      createSSRApp(JsonViewer, {
        value: { x: "<script>alert(1)</script>", enabled: true, score: 72 },
      }),
    );
    expect(html).not.toContain("<script>");
    expect(html).toContain("&lt;script&gt;");
    expect(html).toContain("json-key");
    expect(html).toContain("json-number");
  });
  it("空数据分页依然显示第一页并禁用翻页", async () => {
    const html = await renderToString(
      createSSRApp(AppPagination, {
        page: 1,
        pageSize: 20,
        total: 0,
        loading: false,
      }),
    );
    expect(html).toContain("1 / 1");
    expect((html.match(/disabled/g) || []).length).toBe(2);
  });
});
