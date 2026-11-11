import { describe, it, expect } from "vitest";
import { deriveMetric } from "../src/utils/scoreDerivation";
const detail = (key, x, standards, score) => ({
  calculation: {
    metrics: { [key]: x },
    standards: { [key]: standards },
    rules: {
      interpolation_scores: [10, 35, 65, 85, 100],
      neutral_score: 0,
      score_diff_S: 100,
    },
  },
  score_details: { [key === "jump_3s" ? "jump_score" : key + "_score"]: score },
});
describe("评分推导展示", () => {
  it("使用保存的区间和服务端维度分", () => {
    const r = deriveMetric(
      "play",
      detail("play", 75, [10, 25, 50, 75, 95], 85),
    );
    expect(r.explanation).toContain("P50");
    expect(r.formula).toContain("20");
    expect(r.substitution).toContain("85 分");
  });
  it("反向跳出率使用倒序节点", () => {
    const r = deriveMetric(
      "jump_3s",
      detail("jump_3s", 0.2, [0.05, 0.1, 0.2, 0.3, 0.4], 65),
    );
    expect(r.explanation).toContain("反向");
    expect(r.formula).toContain("X_P75");
    expect(r.substitution).toContain("65 分");
  });
  it("重复基线优先于普通区间", () => {
    const r = deriveMetric(
      "play",
      detail("play", 80, [10, 10, 50, 75, 95], 35),
    );
    expect(r.explanation).toContain("重复节点");
    expect(r.formula).toBeUndefined();
  });
  it("零值保留且缺失快照不编造推导", () => {
    expect(
      deriveMetric("play", detail("play", 0, [10, 25, 50, 75, 95], 10)).actual,
    ).toContain("0");
    expect(deriveMetric("play", null).explanation).toContain("无法还原");
  });
  it("制作难度直接取配置值", () => {
    expect(
      deriveMetric("difficulty", detail("difficulty", "S", null, 100))
        .explanation,
    ).toContain("S级对应基础分 = 100");
  });
});
