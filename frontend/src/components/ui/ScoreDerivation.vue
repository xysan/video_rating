<script setup>
import { computed } from "vue";
import { deriveMetric, numberText } from "../../utils/scoreDerivation";
const props = defineProps({ video: { type: Object, required: true } });
const names = {
  play: "播放量",
  interact: "互动率",
  jump_3s: "3s跳出率",
  progress: "平均播放进度",
  convert: "播转粉率",
  difficulty: "制作难度",
  efficiency: "时效情况",
};
const core = Object.entries(names).slice(0, 5);
const percentiles = ["P10", "P25", "P50", "P75", "P95"];
const snapshot = computed(() => props.video.score_detail?.calculation);
const cards = computed(() =>
  Object.entries(names).map(([key, label]) => ({
    key,
    label,
    ...deriveMetric(key, props.video.score_detail),
  })),
);
const adjustments = computed(() => props.video.score_detail?.bonus_and_penalty);
</script>
<template>
  <div class="derivation-paper">
    <section class="derivation-section">
      <header>
        <span class="eyebrow">01 / BASELINE</span>
        <h3>UP主基线 · {{ video.up_name }}</h3>
        <p>本次评分采用的基线快照；比例指标以小数展示，播放量单位为次。</p>
      </header>
      <div class="derivation-baselines">
        <article
          v-for="[key, label] in core"
          :key="key"
          class="derivation-baseline"
        >
          <h4>{{ label }}</h4>
          <dl>
            <div v-for="(percentile, index) in percentiles" :key="percentile">
              <dt>{{ percentile }}</dt>
              <dd>{{ numberText(snapshot?.standards?.[key]?.[index]) }}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>
    <section class="derivation-section">
      <header>
        <span class="eyebrow">02 / DERIVATION</span>
        <h3>逐维算分推导</h3>
        <p>
          先求维度分，再乘以权重。显示值按精度格式化，总分以服务端完整精度计算结果为准。
        </p>
      </header>
      <div class="derivation-grid">
        <article v-for="item in cards" :key="item.key" class="derivation-card">
          <header>
            <div>
              <h4>{{ item.label }}维度</h4>
              <p>
                实际值 <b>{{ item.actual }}</b>
              </p>
            </div>
            <strong>{{ numberText(item.score) }}<small> 分</small></strong>
          </header>
          <p class="derivation-explanation">{{ item.explanation }}</p>
          <div v-if="item.formula" class="derivation-formula">
            <span>代入公式</span>
            <p>
              <var>X</var> = <b>{{ item.actual }}</b>
            </p>
            <p>{{ item.formula }}</p>
            <p>{{ item.substitution }}</p>
          </div>
          <footer v-if="item.weight != null && item.score != null">
            加权贡献 <b>{{ numberText(item.weight) }}</b> ×
            <b>{{ numberText(item.score) }}</b> ≈
            <strong>{{ numberText(item.weight * item.score, 2) }} 分</strong>
          </footer>
        </article>
      </div>
      <div class="derivation-summary">
        <h4>汇总与加减分</h4>
        <p>
          榜单：{{
            snapshot?.metrics?.tags?.join?.("、") ||
            snapshot?.metrics?.tags ||
            "未填写"
          }}
          · 榜单加分：<b>{{ numberText(adjustments?.ranking_bonus) }}</b> 分
        </p>
        <p>
          投流比例：{{ numberText(snapshot?.metrics?.traffic_ratio) }} ·
          投流扣分：<b>{{ numberText(adjustments?.traffic_penalty) }}</b>
          分（带符号）
        </p>
        <p>
          综合得分 = 加权基础分
          {{ numberText(video.score_detail?.base_score) }} + 榜单加分
          {{ numberText(adjustments?.ranking_bonus) }} + 投流扣分（{{
            numberText(adjustments?.traffic_penalty)
          }}） = <strong>{{ numberText(video.total_score) }} 分</strong>
        </p>
      </div>
    </section>
  </div>
</template>
<style scoped>
.derivation-paper,
.derivation-section {
  display: grid;
  gap: var(--space-4);
  min-width: 0;
}
.derivation-paper {
  gap: var(--space-6, 2rem);
  margin-block: var(--space-4);
}
.derivation-section > header p {
  color: var(--color-muted);
  font-size: var(--text-sm);
  margin-top: var(--space-2);
  line-height: 1.7;
}
.derivation-baselines {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-3);
}
.derivation-baseline,
.derivation-card,
.derivation-summary {
  padding: clamp(1rem, 2vw, 1.5rem);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-input);
  background: var(--color-input);
  min-width: 0;
  overflow-wrap: anywhere;
}
.derivation-baseline h4 {
  font-size: var(--text-sm);
  margin: 0 0 var(--space-3);
}
.derivation-baseline dl {
  margin: 0;
  display: grid;
  gap: var(--space-2);
}
.derivation-baseline dl > div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  flex-wrap: wrap;
  font-size: var(--text-sm);
}
.derivation-baseline dt {
  color: var(--color-muted);
}
.derivation-baseline dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}
.derivation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}
.derivation-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.derivation-card header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: start;
  flex-wrap: wrap;
}
.derivation-card h4,
.derivation-summary h4 {
  margin: 0;
}
.derivation-card header p {
  font-size: var(--text-sm);
  color: var(--color-muted);
  margin-top: var(--space-2);
}
.derivation-card header > strong {
  font: 600 var(--text-heading) var(--font-display);
  color: var(--color-brand);
}
.derivation-card small {
  font: normal var(--text-sm) var(--font-body);
}
.derivation-explanation,
.derivation-summary p {
  line-height: 1.8;
  font-size: var(--text-sm);
}
.derivation-formula {
  padding: var(--space-3);
  border-radius: var(--radius-small);
  background: var(--color-nav);
  line-height: 1.9;
  font-variant-numeric: tabular-nums;
  font-size: var(--text-sm);
}
.derivation-formula > span {
  color: var(--color-muted);
}
.derivation-formula var,
.derivation-formula b,
.derivation-summary strong {
  color: var(--color-brand);
}
.derivation-card footer {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
  font-size: var(--text-intro);
  color: var(--color-brand);
  font-weight: 700;
  line-height: 1.8;
}
.derivation-summary {
  border-color: var(--color-brand);
  box-shadow: var(--shadow-high-rest);
}
.derivation-summary h4 {
  font-size: var(--text-intro);
}
.derivation-summary b {
  font-size: var(--text-intro);
  color: var(--color-brand);
  font-variant-numeric: tabular-nums;
}
.derivation-summary p:last-child {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  font-size: var(--text-lg);
  font-weight: 600;
}
.derivation-summary strong {
  font-size: var(--text-heading);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
@media (max-width: 60rem) {
  .derivation-baselines {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 40rem) {
  .derivation-baselines {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .derivation-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
