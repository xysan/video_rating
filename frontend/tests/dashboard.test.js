import { describe, expect, it } from "vitest";
import {
  scoreOf,
  isHighScore,
  formatCount,
  nextScroll,
} from "../src/utils/dashboard";
describe("看板数据展示", () => {
  it("缺失分数不能变成零分", () => {
    expect(scoreOf({ score: null })).toBeNull();
    expect(scoreOf({ score: 0 })).toBe(0);
    expect(scoreOf({ total_score: "85.00" })).toBe(85);
    expect(scoreOf({ score: "invalid" })).toBeNull();
  });
  it("85分边界与服务端高分标记", () => {
    expect(isHighScore({ score: 85 })).toBe(true);
    expect(isHighScore({ score: 84.99 })).toBe(false);
    expect(isHighScore({ score: null })).toBe(false);
    expect(isHighScore({ is_high_score: true })).toBe(true);
  });
  it("互动数据缺失与真实零值分别显示", () => {
    expect(formatCount(null)).toBe("—");
    expect(formatCount(0)).toBe("0");
    expect(formatCount(12345)).toBe("1.2万");
    expect(formatCount(120000000)).toBe("1.2亿");
  });
  it("滚动到两端后循环，单屏数据不滚动", () => {
    expect(nextScroll(700, 1000, 300, 1)).toBe(0);
    expect(nextScroll(0, 1000, 300, -1)).toBe(700);
    expect(nextScroll(0, 200, 300, 1)).toBe(0);
    expect(nextScroll(600, 1000, 300, 1)).toBe(700);
  });
});

import { createSSRApp } from "vue";
import { renderToString } from "vue/server-renderer";
import VideoCard from "../src/components/dashboard/VideoCard.vue";
describe("视频卡片渲染", () => {
  it("待采集状态不会渲染成零分，缺失指标保留占位", async () => {
    const html = await renderToString(
      createSSRApp(VideoCard, {
        video: { title: "测试视频", score: null, play_count: 0 },
      }),
    );
    expect(html).toContain("数据采集中");
    expect(html).not.toContain("video-card-high");
    expect(html).toContain("暂无封面");
    expect(html).toContain("<dd>0</dd>");
  });
  it("85分触发高分样式，完整呈现编导与得分", async () => {
    const html = await renderToString(
      createSSRApp(VideoCard, {
        video: { title: "测试视频", total_score: 85, director: "测试编导" },
      }),
    );
    expect(html).toContain("video-card-high");
    expect(html).toContain("85.00");
    expect(html).toContain("测试编导");
  });
});
