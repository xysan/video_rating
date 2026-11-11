<script setup>
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useRoute } from "vue-router";
import { session } from "../auth/session";
import { fetchScores, percent } from "../api/scores";
import { formatCount } from "../utils/dashboard";
import GlassPanel from "../components/ui/GlassPanel.vue";
import AppMultiSelect from "../components/ui/AppMultiSelect.vue";
import "../styles/scores-design.css";
import GlassPicker from "../components/ui/GlassPicker.vue";
import AppButton from "../components/ui/AppButton.vue";
import AppPagination from "../components/ui/AppPagination.vue";
import ScoreDerivation from "../components/ui/ScoreDerivation.vue";
import AppDialog from "../components/ui/AppDialog.vue";
import { api } from "../api/client";
import { toast, errorMessage } from "../components/ui/toast";
const route = useRoute();
const admin = computed(
  () => route.path.startsWith("/admin/") && session.user?.role === "admin",
);
const blank = () => ({
  up_names: [],
  directors: [],
  date_from: "",
  date_to: "",
  is_published_15_days: false,
  sort_by: "publish_date",
  sort_order: "desc",
});
const options = ref({ up_names: [], directors: [] }),
  saving = ref(false),
  exporting = ref(false),
  exportFormat = ref("csv");
const extras = reactive({
  difficulty: null,
  efficiency: null,
  traffic_ratio: null,
});
api
  .get("/api/scores/filters")
  .then((r) => (options.value = r.data))
  .catch((e) => toast(errorMessage(e, "筛选项加载失败"), "error"));
const filters = reactive(blank());
let applied = blank(),
  controller,
  sequence = 0;
const rows = ref([]),
  page = ref(1),
  size = ref(20),
  total = ref(0),
  loading = ref(false),
  error = ref(""),
  selected = ref(null);
async function load() {
  const run = ++sequence;
  controller?.abort();
  controller = new AbortController();
  loading.value = true;
  error.value = "";
  rows.value = [];
  selected.value = null;
  try {
    const params = {
      page: page.value,
      page_size: size.value,
      ...Object.fromEntries(
        Object.entries(applied).filter(([, value]) => value),
      ),
    };
    const result = await fetchScores(admin.value, params, controller.signal);
    if (run !== sequence) return;
    rows.value = result.items;
    total.value = result.total;
  } catch (err) {
    if (run !== sequence || err.code === "ERR_CANCELED") return;
    error.value = errorMessage(err, "评分数据加载失败，请重试");
    total.value = 0;
    toast(error.value, "error");
  } finally {
    if (run === sequence) loading.value = false;
  }
}
function search() {
  if (
    filters.date_from &&
    filters.date_to &&
    filters.date_from > filters.date_to
  ) {
    toast("开始日期不能晚于结束日期", "error");
    return;
  }
  applied = Object.fromEntries(
    Object.entries(filters).map(([key, value]) => [
      key,
      typeof value === "string" ? value.trim() : value,
    ]),
  );
  page.value = 1;
  load();
}
function reset() {
  Object.assign(filters, blank());
}
watch(filters, search, { deep: true });
function changePage(value) {
  page.value = value;
  load();
}
function changeSize(value) {
  size.value = value;
  page.value = 1;
  load();
}
watch(
  () => route.path,
  () => {
    Object.assign(filters, blank());
    applied = blank();
    page.value = 1;
    load();
  },
  { immediate: true },
);
onBeforeUnmount(() => {
  sequence++;
  controller?.abort();
});

function openDetail(row) {
  selected.value = row;
  Object.assign(extras, {
    difficulty: row.difficulty || null,
    efficiency: row.efficiency || null,
    traffic_ratio: row.traffic_ratio == null ? null : Number(row.traffic_ratio),
  });
}
async function saveExtras() {
  saving.value = true;
  try {
    const { data } = await api.put(
      `/api/admin/videos/${selected.value.id}/extras`,
      {
        ...extras,
        traffic_ratio:
          extras.traffic_ratio === "" ? null : extras.traffic_ratio,
      },
    );
    Object.assign(selected.value, data);
    toast("已保存到数据库并重算");
  } catch (e) {
    toast(errorMessage(e, "保存失败"), "error");
  } finally {
    saving.value = false;
  }
}
async function download() {
  exporting.value = true;
  try {
    const { data } = await api.get("/api/admin/scores/export", {
      params: { ...applied, format: exportFormat.value },
      paramsSerializer: { indexes: null },
      responseType: "blob",
    });
    const url = URL.createObjectURL(data),
      a = document.createElement("a");
    a.href = url;
    a.download = "视频得分." + exportFormat.value;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast("已发起下载");
  } catch (e) {
    toast(errorMessage(e, "导出失败"), "error");
  } finally {
    exporting.value = false;
  }
}
</script>
<template>
  <section class="data-page scores-page">
    <header class="data-page-heading">
      <div>
        <p class="eyebrow">VIDEO PERFORMANCE</p>
        <h1>视频15日得分</h1>
      </div>
    </header>
    <GlassPanel class="score-toolbar">
      <div class="score-filter-fields">
        <AppMultiSelect
          id="score-up"
          label="UP主"
          v-model="filters.up_names"
          :options="options.up_names"
        />
        <AppMultiSelect
          id="score-director"
          label="编导"
          v-model="filters.directors"
          :options="options.directors"
        />
        <div class="score-date-range">
          <GlassPicker
            id="filter-start"
            v-model="filters.date_from"
            date
            label="开始日期"
            :max="filters.date_to || undefined"
          /><GlassPicker
            id="filter-end"
            v-model="filters.date_to"
            date
            label="结束日期"
            :min="filters.date_from || undefined"
          />
        </div>
      </div>
      <div class="score-toolbar-actions">
        <AppButton variant="secondary" @click="reset">重置</AppButton>
        <div class="score-right-actions">
          <label class="age-toggle"
            ><input
              type="checkbox"
              v-model="filters.is_published_15_days"
            />发布满15日</label
          >
          <div class="sort-group">
            <GlassPicker
              v-model="filters.sort_by"
              label="排序依据"
              :options="[
                { value: 'publish_date', label: '发布时间' },
                { value: 'total_score', label: '总分' },
              ]"
            /><button
              type="button"
              :aria-label="
                filters.sort_order === 'desc' ? '切换为升序' : '切换为降序'
              "
              @click="
                filters.sort_order =
                  filters.sort_order === 'desc' ? 'asc' : 'desc'
              "
            >
              {{ filters.sort_order === "desc" ? "↓ 降序" : "↑ 升序" }}
            </button>
          </div>
          <div v-if="admin" class="export-group">
            <GlassPicker
              v-model="exportFormat"
              label="导出格式"
              :options="[
                { value: 'csv', label: 'CSV' },
                { value: 'xlsx', label: 'XLSX' },
              ]"
            /><AppButton
              :loading="exporting"
              :disabled="loading"
              @click="download"
              >导出</AppButton
            >
          </div>
        </div>
      </div>
    </GlassPanel>
    <GlassPanel class="table-panel" :aria-busy="loading"
      ><div class="table-scroll">
        <table class="data-table">
          <caption class="sr-only">
            视频评分及核心指标
          </caption>
          <thead>
            <tr>
              <th scope="col">视频 / 发布时间</th>
              <th scope="col">UP 主 / 编导</th>
              <th scope="col">总分</th>
              <th scope="col">播放量</th>

              <th scope="col">互动率</th>
              <th scope="col">3s 跳出率</th>
              <th scope="col">平均播放进度</th>
              <th scope="col">播转粉率</th>
              <th v-if="admin" scope="col">操作</th>
            </tr>
          </thead>
          <tbody v-if="loading">
            <tr v-for="n in 6" :key="n">
              <td :colspan="admin ? 9 : 8">
                <div class="row-skeleton" aria-label="正在加载" />
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr v-for="row in rows" :key="row.id">
              <td class="title-cell">
                <strong :title="row.video_title">{{
                  row.video_title || row.title
                }}</strong
                ><small>{{ row.publish_date }}</small>
              </td>
              <td>
                <span>{{ row.up_name }}</span
                ><small>{{ "编导：" + (row.director || "无") }}</small>
              </td>
              <td>
                <strong class="table-score">{{
                  row.total_score == null
                    ? "待评分"
                    : Number(row.total_score).toFixed(2)
                }}</strong>
              </td>
              <td>{{ formatCount(row.snapshot_play_count) }}</td>

              <td>{{ percent(row.interact_rate) }}</td>
              <td>{{ percent(row.jump_3s) }}</td>
              <td>{{ percent(row.progress) }}</td>
              <td>{{ percent(row.convert_rate) }}</td>
              <td v-if="admin">
                <AppButton variant="secondary" @click="openDetail(row)"
                  >查看明细</AppButton
                >
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td :colspan="admin ? 9 : 8" class="table-empty">
                <p>{{ error || "没有符合筛选条件的视频" }}</p>
                <AppButton v-if="error" variant="secondary" @click="load"
                  >重新加载</AppButton
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <AppPagination
        :page="page"
        :page-size="size"
        :total="total"
        :loading="loading"
        @page="changePage"
        @size="changeSize"
    /></GlassPanel>
    <AppDialog
      v-if="admin"
      class="score-detail-dialog"
      :open="!!selected"
      title="视频计算明细"
      :busy="saving"
      @close="selected = null"
    >
      <template v-if="selected">
        <div class="detail-overview">
          <div>
            <p class="eyebrow">PERFORMANCE BREAKDOWN</p>
            <h3>{{ selected.video_title || selected.title }}</h3>
            <p>{{ selected.up_name }} · {{ selected.publish_date }}</p>
          </div>
          <div class="detail-total">
            <span>综合得分</span
            ><strong>{{
              selected.total_score == null
                ? "待评分"
                : Number(selected.total_score).toFixed(2)
            }}</strong>
          </div>
        </div>
        <ScoreDerivation :video="selected" />
        <form
          id="extras-edit-form"
          class="extras-edit-card"
          @submit.prevent="saveExtras"
        >
          <header>
            <h3>编辑数据</h3>
            <p>保存后写入数据库，并按当前规则重新计算得分。</p>
          </header>
          <div class="extras-edit-grid">
            <label
              >制作难度<select v-model="extras.difficulty" :disabled="saving">
                <option :value="null">未填写</option>
                <option>S</option>
                <option>A</option>
                <option>B</option>
              </select></label
            ><label
              >时效情况<select v-model="extras.efficiency" :disabled="saving">
                <option :value="null">未填写</option>
                <option
                  v-for="x in [
                    '按时',
                    '推迟1-2天',
                    '推迟2-3天',
                    '推迟3-5天',
                    '推迟5天以上',
                  ]"
                  :key="x"
                >
                  {{ x }}
                </option>
              </select></label
            ><label
              >投流比例 <small>0—1</small
              ><input
                type="number"
                min="0"
                max="1"
                step="any"
                v-model.number="extras.traffic_ratio"
                :disabled="saving"
                placeholder="例如 0.3"
            /></label>
          </div>
        </form>
      </template>
      <template #footer
        ><span class="detail-save-note">修改仅在保存成功后生效</span
        ><AppButton
          variant="secondary"
          :disabled="saving"
          @click="selected = null"
          >取消</AppButton
        ><AppButton type="submit" form="extras-edit-form" :loading="saving"
          >保存并重算</AppButton
        ></template
      >
    </AppDialog>
  </section>
</template>
