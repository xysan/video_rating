export function numberText(value, digits = 6) {
  if (value == null || value === "" || !Number.isFinite(Number(value)))
    return "—";
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: digits,
  }).format(Number(value));
}
// 仅解释服务端保存的计算快照，不参与业务计分或写入。
export function deriveMetric(key, detail) {
  const snapshot = detail?.calculation;
  const rules = snapshot?.rules;
  const x = snapshot?.metrics?.[key];
  const score =
    detail?.score_details?.[key === "jump_3s" ? "jump_score" : key + "_score"];
  const result = {
    score,
    weight: rules?.["weight_" + key],
    actual: x == null ? "未填写" : String(x),
    explanation: "暂无完整计算快照，无法还原推导过程。",
  };
  if (!rules || !snapshot?.metrics) return result;
  if (key === "difficulty" || key === "efficiency") {
    const mapped =
      key === "difficulty"
        ? rules["score_diff_" + x]
        : rules.efficiency_scores?.[x];
    result.explanation =
      mapped == null
        ? `未填写或未匹配，采用缺失项默认分值 ${numberText(rules.neutral_score)} 分。`
        : `${x}${key === "difficulty" ? "级" : ""}对应基础分 = ${numberText(mapped)} 分。`;
    return result;
  }
  if (x == null) {
    result.explanation = "核心指标缺失，无法计算。";
    return result;
  }
  const standards = snapshot.standards?.[key],
    points = rules.interpolation_scores;
  if (
    !Array.isArray(standards) ||
    standards.length !== 5 ||
    !Array.isArray(points) ||
    points.length !== 5
  )
    return result;
  const reverse = key === "jump_3s";
  const nodes = standards.map((value, i) => ({
    value,
    name: ["P10", "P25", "P50", "P75", "P95"][i],
  }));
  if (reverse) nodes.reverse();
  result.actual = numberText(x) + (key === "play" ? " 次" : "（比例小数）");
  // 相邻节点相同的优先分支与后端一致，不能按普通插值展示。
  for (let i = 0; i < 4; i++) {
    if (nodes[i].value === nodes[i + 1].value) {
      const first = reverse ? x >= nodes[i].value : x <= nodes[i].value;
      result.explanation = `${nodes[i].name} 与 ${nodes[i + 1].name} 均为 ${numberText(nodes[i].value)}，优先采用重复节点规则；X ${first ? (reverse ? "≥" : "≤") : reverse ? "<" : ">"} ${numberText(nodes[i].value)}，直接取 ${numberText(points[i + (first ? 0 : 1)])} 分。`;
      return result;
    }
  }
  if (reverse ? x >= nodes[0].value : x <= nodes[0].value) {
    result.explanation = `X ${reverse ? "≥" : "≤"} ${nodes[0].name}（${numberText(nodes[0].value)}），取边界分 ${numberText(points[0])} 分。`;
    return result;
  }
  for (let i = 0; i < 4; i++) {
    if (reverse ? x >= nodes[i + 1].value : x <= nodes[i + 1].value) {
      const a = nodes[i],
        b = nodes[i + 1],
        delta = points[i + 1] - points[i];
      result.explanation = `实际值 X 落入 ${a.name}（${numberText(a.value)}）与 ${b.name}（${numberText(b.value)}）区间${reverse ? "，按反向指标插值" : ""}。`;
      result.formula = `${numberText(points[i])} + ${numberText(delta)} × (X − X_${a.name}) ÷ (X_${b.name} − X_${a.name})`;
      result.substitution = `≈ ${numberText(points[i])} + ${numberText(delta)} × (${numberText(x)} − ${numberText(a.value)}) ÷ (${numberText(b.value)} − ${numberText(a.value)}) = ${numberText(score)} 分`;
      return result;
    }
  }
  result.explanation = `X ${reverse ? "<" : ">"} ${nodes[4].name}（${numberText(nodes[4].value)}），取边界分 ${numberText(points[4])} 分。`;
  return result;
}
