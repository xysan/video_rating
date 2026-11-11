<script setup>
import { ref, computed, onMounted } from "vue";
import {
  PhPencilSimple,
  PhPlus,
  PhTrash,
  PhSlidersHorizontal,
  PhUsers,
} from "@phosphor-icons/vue";
import "../styles/settings-design.css";
import { api } from "../api/client";
import { session } from "../auth/session";
import { useRouter } from "vue-router";
import GlassPanel from "../components/ui/GlassPanel.vue";
import AppButton from "../components/ui/AppButton.vue";
import AppDialog from "../components/ui/AppDialog.vue";
import RuleFields from "../components/ui/RuleFields.vue";
import { toast, errorMessage } from "../components/ui/toast";
const router = useRouter(),
  tab = ref("configs"),
  category = ref("algorithm"),
  configs = ref([]),
  users = ref([]),
  loading = ref(false),
  saving = ref(false),
  editing = ref(false),
  key = ref(""),
  value = ref(null),
  description = ref(""),
  newUp = ref(false),
  upName = ref(""),
  error = ref("");
const labels = {
  calculation_age_days: "评分时间节点",
  interpolation_scores: "百分位对应分值",
  efficiency_scores: "效率分值",
  ranking_bonuses: "榜单加分",
  traffic_penalty_thresholds: "投流扣分规则",
  score_diff_S: "S级难度分值",
  score_diff_A: "A级难度分值",
  score_diff_B: "B级难度分值",
  weight_play: "播放量权重",
  weight_interact: "互动率权重",
  weight_jump_3s: "3s跳出率权重",
  weight_progress: "平均播放进度权重",
  weight_convert: "播转粉率权重",
  weight_difficulty: "制作难度权重",
  weight_efficiency: "效率权重",
  neutral_score: "缺失项默认分值",
  metric_fields: "飞书字段对应关系",
};
function label(k) {
  return k.startsWith("up_standards_") ? k.slice(13) : labels[k] || k;
}
function group(k) {
  return k.startsWith("up_standards_")
    ? "standards"
    : k.startsWith("weight_") ||
        k.startsWith("score_diff_") ||
        [
          "efficiency_scores",
          "ranking_bonuses",
          "traffic_penalty_thresholds",
        ].includes(k)
      ? "weights"
      : "algorithm";
}
const visible = computed(() =>
  configs.value.filter((c) => group(c.config_key) === category.value),
);
const weightOrder = [
  "weight_difficulty",
  "weight_efficiency",
  "weight_play",
  "weight_interact",
  "weight_jump_3s",
  "weight_progress",
  "weight_convert",
];
const weightRank = (key) => {
  const index = weightOrder.indexOf(key);
  return index < 0 ? weightOrder.length : index;
};
const configGroups = computed(() => {
  const difficultyKeys = ["score_diff_S", "score_diff_A", "score_diff_B"];
  const difficulty = difficultyKeys
    .map((key) => visible.value.find((c) => c.config_key === key))
    .filter(Boolean);
  if (category.value !== "weights") return [{ name: "", items: visible.value }];
  const fixedKeys = [
    "efficiency_scores",
    "ranking_bonuses",
    "traffic_penalty_thresholds",
  ];
  return [
    { name: "制作难度分值", items: difficulty },
    {
      name: "固定得分项",
      items: visible.value.filter((c) => fixedKeys.includes(c.config_key)),
    },
    {
      name: "权重项",
      items: visible.value
        .filter((c) => c.config_key.startsWith("weight"))
        .sort((a, b) => weightRank(a.config_key) - weightRank(b.config_key)),
    },
  ].filter((group) => group.items.length);
});
const dimensions = {
  play: "播放量",
  interact: "互动率",
  jump_3s: "3s跳出率",
  progress: "平均播放进度",
  convert: "播转粉率",
};
const percentiles = ["P10", "P25", "P50", "P75", "P95"];
const categoryNames = {
  algorithm: "算法类",
  weights: "权重规则",
  standards: "UP主基线",
};
const categoryDescriptions = {
  algorithm: "定义评分周期与指标转换方式。",
  weights: "调整各维度的贡献、奖励与扣分规则。",
  standards: "为每位 UP 主维护独立的五维百分位基线。",
};
const editingBaseline = computed(
  () => newUp.value || key.value.startsWith("up_standards_"),
);
function displayValue(v) {
  return v == null
    ? "未设置"
    : typeof v === "number"
      ? new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 6 }).format(v)
      : String(v);
}
const fieldNames = {
  ...dimensions,
  difficulty: "制作难度",
  efficiency: "时效情况",
  traffic_ratio: "投流比例",
  tags: "榜单",
  lower: "扣分起始比例",
  upper: "高额扣分比例",
  middle_penalty: "中档扣分",
  high_penalty: "高档扣分",
  tag: "榜单名称",
  score: "分值",
};
function entries(v, path = "") {
  if (v === null || typeof v !== "object")
    return [{ name: path || "当前值", value: displayValue(v) }];
  return Object.entries(v).flatMap(([k, x]) =>
    entries(
      x,
      [
        path,
        Array.isArray(v)
          ? v.length === 5
            ? percentiles[k]
            : `规则 ${Number(k) + 1}`
          : fieldNames[k] || k,
      ]
        .filter(Boolean)
        .join(" · "),
    ),
  );
}
function tabKeys(event, items, current, set) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const i = items.indexOf(current);
  const n =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? items.length - 1
        : (i + (event.key === "ArrowRight" ? 1 : -1) + items.length) %
          items.length;
  set(items[n]);
  event.currentTarget.parentElement.querySelectorAll("[role=tab]")[n]?.focus();
}
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [c, u] = await Promise.all([
      api.get("/api/admin/configs"),
      api.get("/api/admin/users"),
    ]);
    configs.value = c.data;
    users.value = u.data.map((x) => ({ ...x, draftRole: x.role }));
  } catch (e) {
    error.value = errorMessage(e, "加载失败");
    toast(error.value, "error");
  } finally {
    loading.value = false;
  }
}
function edit(c) {
  newUp.value = false;
  key.value = c.config_key;
  value.value = JSON.parse(JSON.stringify(c.config_value));
  description.value = c.description;
  editing.value = true;
}
function add() {
  newUp.value = true;
  upName.value = "";
  value.value = Object.fromEntries(
    ["play", "interact", "jump_3s", "progress", "convert"].map((k) => [
      k,
      [0, 0, 0, 0, 0],
    ]),
  );
  description.value = "管理员新增基线";
  editing.value = true;
}
async function save() {
  if (saving.value) return;
  const k = newUp.value ? "up_standards_" + upName.value.trim() : key.value;
  if (newUp.value && !upName.value.trim()) {
    toast("请填写 UP 主名称", "error");
    return;
  }
  if (newUp.value && configs.value.some((c) => c.config_key === k)) {
    toast("该 UP 主基线已存在，请从列表点击编辑", "error");
    return;
  }
  saving.value = true;
  try {
    await api.put("/api/admin/configs/" + encodeURIComponent(k), {
      config_value: value.value,
      description: description.value,
    });
    editing.value = false;
    await load();
    toast("配置已写入数据库");
  } catch (e) {
    toast(errorMessage(e, "保存失败"), "error");
  } finally {
    saving.value = false;
  }
}
async function role(u) {
  if (saving.value || u.role === u.draftRole) return;
  if (
    u.id === session.user.id &&
    u.draftRole === "member" &&
    !window.confirm("保存后你将失去管理权限，是否继续？")
  )
    return;
  saving.value = true;
  try {
    const { data } = await api.put(`/api/admin/users/${u.id}/role`, {
      role: u.draftRole,
    });
    if (u.id === session.user.id) {
      session.user = { ...session.user, role: data.role };
      if (data.role !== "admin") {
        await router.replace("/forbidden");
        return;
      }
    }
    await load();
    toast("角色已写入数据库");
  } catch (e) {
    u.draftRole = u.role;
    toast(errorMessage(e, "保存失败"), "error");
  } finally {
    saving.value = false;
  }
}
async function removeConfig(c) {
  if (saving.value) return;
  if (!window.confirm("删除该 UP 主基线后，后续评分将提示缺失基线。确认删除？"))
    return;
  saving.value = true;
  try {
    await api.delete("/api/admin/configs/" + encodeURIComponent(c.config_key));
    await load();
    toast("基线已从数据库删除");
  } catch (e) {
    toast(errorMessage(e, "删除失败"), "error");
  } finally {
    saving.value = false;
  }
}
onMounted(load);
</script>
<template>
  <section class="data-page settings-console">
    <header class="data-page-heading">
      <div>
        <p class="eyebrow">WORKSPACE CONTROL</p>
        <h1>管理设置</h1>
        <p class="console-intro">让规则清晰，让创作有据可依。</p>
      </div>
      <span class="console-status">管理员控制台</span>
    </header>
    <div
      class="console-pill"
      role="tablist"
      aria-label="管理设置主导航"
      :class="{ 'show-users': tab === 'users' }"
    >
      <span class="pill-slider" aria-hidden="true" /><button
        v-for="(name, id) in { configs: '算法配置', users: '用户管理' }"
        :key="id"
        :id="'main-' + id"
        role="tab"
        :aria-selected="tab === id"
        :aria-controls="'console-' + id"
        :tabindex="tab === id ? 0 : -1"
        @click="tab = id"
        @keydown="tabKeys($event, ['configs', 'users'], tab, (v) => (tab = v))"
      >
        <PhSlidersHorizontal v-if="id === 'configs'" /><PhUsers v-else />{{
          name
        }}
      </button>
    </div>
    <div
      v-if="tab === 'configs'"
      class="console-subnav"
      role="tablist"
      aria-label="配置分类"
    >
      <button
        v-for="(name, id) in categoryNames"
        :key="id"
        :id="'category-' + id"
        role="tab"
        :aria-selected="category === id"
        :aria-controls="'category-content-' + id"
        :tabindex="category === id ? 0 : -1"
        @click="category = id"
        @keydown="
          tabKeys(
            $event,
            Object.keys(categoryNames),
            category,
            (v) => (category = v),
          )
        "
      >
        {{ name
        }}<span>{{
          configs.filter((c) => group(c.config_key) === id).length
        }}</span>
      </button>
    </div>
    <GlassPanel
      :id="'console-' + tab"
      class="console-content"
      role="tabpanel"
      :aria-labelledby="'main-' + tab"
      :aria-busy="loading"
    >
      <header class="console-section-head">
        <div>
          <h2>{{ tab === "users" ? "团队成员" : categoryNames[category] }}</h2>
          <p>
            {{
              tab === "users"
                ? "管理成员身份与访问权限，角色修改保存后生效。"
                : categoryDescriptions[category]
            }}
          </p>
        </div>
        <AppButton
          v-if="tab === 'configs' && category === 'standards'"
          :disabled="loading || saving"
          @click="add"
          ><PhPlus />新增UP主基线</AppButton
        >
      </header>
      <div class="console-scroll">
        <div
          v-if="loading"
          class="console-config-grid"
          role="status"
          aria-label="正在加载设置"
        >
          <div v-for="n in 6" :key="n" class="console-skeleton" />
        </div>
        <div v-else-if="error" class="console-empty">
          <p>{{ error }}</p>
          <AppButton variant="secondary" @click="load">重试</AppButton>
        </div>
        <section
          v-else-if="tab === 'configs'"
          :id="'category-content-' + category"
          role="tabpanel"
          :aria-labelledby="'category-' + category"
        >
          <div v-if="!visible.length" class="console-empty">
            {{
              category === "standards"
                ? "尚无 UP 主基线，点击右上角新增。"
                : "暂无配置"
            }}
          </div>
          <div v-else-if="category === 'standards'" class="baseline-list">
            <article
              v-for="c in visible"
              :key="c.config_key"
              class="console-card baseline-card"
            >
              <header>
                <div>
                  <small>CREATOR STANDARDS</small>
                  <h3>UP主：{{ label(c.config_key) }}</h3>
                </div>
                <div class="config-card-actions">
                  <button
                    class="console-icon-button"
                    :aria-label="'编辑' + label(c.config_key) + '基线'"
                    @click="edit(c)"
                  >
                    <PhPencilSimple /></button
                  ><button
                    class="console-icon-button"
                    :disabled="saving"
                    :aria-label="'删除' + label(c.config_key) + '基线'"
                    @click="removeConfig(c)"
                  >
                    <PhTrash />
                  </button>
                </div>
              </header>
              <div class="baseline-metrics">
                <section v-for="(name, metric) in dimensions" :key="metric">
                  <h4>{{ name }}</h4>
                  <dl>
                    <div
                      v-for="(percentile, index) in percentiles"
                      :key="percentile"
                    >
                      <dt>{{ percentile }}</dt>
                      <dd>
                        {{ displayValue(c.config_value?.[metric]?.[index]) }}
                      </dd>
                    </div>
                  </dl>
                </section>
              </div>
            </article>
          </div>
          <div v-else class="config-groups">
            <section
              v-for="configGroup in configGroups"
              :key="configGroup.name"
              class="config-group"
            >
              <h3 v-if="configGroup.name" class="config-group-title">
                {{ configGroup.name }}
              </h3>
              <div class="console-config-grid">
                <article
                  v-for="c in configGroup.items"
                  :key="c.config_key"
                  class="console-card config-card"
                >
                  <header>
                    <h3>{{ label(c.config_key) }}</h3>
                    <button
                      class="console-icon-button"
                      :aria-label="'编辑' + label(c.config_key)"
                      @click="edit(c)"
                    >
                      <PhPencilSimple />
                    </button>
                  </header>
                  <dl class="config-values">
                    <div
                      v-for="item in entries(c.config_value)"
                      :key="item.name"
                    >
                      <dt>
                        {{
                          c.config_key === "calculation_age_days"
                            ? "发布后几天"
                            : item.name
                        }}
                      </dt>
                      <dd>{{ item.value }}</dd>
                    </div>
                  </dl>
                </article>
              </div>
            </section>
          </div>
        </section>
        <div v-else class="console-users">
          <article
            v-for="u in users"
            :key="u.id"
            class="console-card console-user"
          >
            <div class="user-identity">
              <span class="console-avatar">{{
                Array.from(u.display_name || u.username)[0]
              }}</span>
              <div>
                <h3>
                  {{ u.display_name || u.username
                  }}<span v-if="u.id === session.user.id" class="self-label"
                    >你</span
                  >
                </h3>
                <p>{{ u.username }}</p>
              </div>
            </div>
            <span
              class="user-role-badge"
              :class="{ 'is-admin': u.role === 'admin' }"
              >{{ u.role === "admin" ? "管理员" : "普通成员" }}</span
            >
            <div class="user-role-actions">
              <div
                class="role-switch"
                role="group"
                :aria-label="u.username + '的角色'"
              >
                <button
                  v-for="(name, id) in { member: '普通成员', admin: '管理员' }"
                  :key="id"
                  :aria-pressed="u.draftRole === id"
                  :disabled="saving"
                  @click="u.draftRole = id"
                >
                  {{ name }}
                </button>
              </div>
              <AppButton
                :disabled="saving || u.role === u.draftRole"
                @click="role(u)"
                >保存角色</AppButton
              >
            </div>
          </article>
          <p v-if="!users.length" class="console-empty">暂无用户</p>
        </div>
      </div>
    </GlassPanel>
    <AppDialog
      class="settings-edit-dialog"
      :open="editing"
      :busy="saving"
      :title="newUp ? '新增UP主基线' : label(key)"
      @close="editing = false"
    >
      <form id="settings-edit-form" @submit.prevent="save">
        <div class="settings-editor-intro">
          <p>
            {{
              editingBaseline
                ? "五个维度各维护五个升序节点；比例指标使用小数，例如 0.25 表示 25%。"
                : "修改规则数值，保存时将由后端校验并写入数据库。"
            }}
          </p>
        </div>
        <label v-if="newUp" class="baseline-name"
          >UP主名称<input
            v-model="upName"
            required
            placeholder="填写完整 UP 主名称"
            :disabled="saving"
        /></label>
        <div v-if="editingBaseline && value" class="baseline-editor">
          <fieldset
            v-for="(name, metric) in dimensions"
            :key="metric"
            class="baseline-editor-row"
            :disabled="saving"
          >
            <legend>{{ name }}</legend>
            <div class="baseline-inputs">
              <label
                v-for="(percentile, index) in percentiles"
                :key="percentile"
                >{{ percentile
                }}<input
                  v-model.number="value[metric][index]"
                  type="number"
                  step="any"
                  required
                  :aria-label="name + ' ' + percentile"
              /></label>
            </div>
          </fieldset>
        </div>
        <fieldset v-else class="settings-rule-form" :disabled="saving">
          <RuleFields v-model="value" label="配置内容" />
        </fieldset>
      </form>
      <template #footer
        ><span class="settings-save-hint">保存成功后刷新数据库列表</span
        ><AppButton
          variant="secondary"
          :disabled="saving"
          @click="editing = false"
          >取消</AppButton
        ><AppButton type="submit" form="settings-edit-form" :loading="saving"
          >保存配置</AppButton
        ></template
      >
    </AppDialog>
  </section>
</template>
