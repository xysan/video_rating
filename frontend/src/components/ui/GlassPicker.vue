<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import {
  PhCaretDown,
  PhCalendarBlank,
  PhCaretLeft,
  PhCaretRight,
} from "@phosphor-icons/vue";
const props = defineProps({
  modelValue: String,
  label: String,
  id: String,
  options: Array,
  date: Boolean,
  min: String,
  max: String,
});
const emit = defineEmits(["update:modelValue"]);
const root = ref(null),
  trigger = ref(null),
  open = ref(false),
  month = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
const display = computed(() =>
  props.date
    ? props.modelValue || "选择日期"
    : props.options?.find((x) => x.value === props.modelValue)?.label ||
      "请选择",
);
const days = computed(() => {
  const y = month.value.getFullYear(),
    m = month.value.getMonth(),
    offset = (new Date(y, m, 1).getDay() + 6) % 7;
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(y, m, i - offset + 1),
      value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    return {
      value,
      day: d.getDate(),
      current: d.getMonth() === m,
      disabled: !!(
        (props.min && value < props.min) ||
        (props.max && value > props.max)
      ),
    };
  });
});
function show() {
  open.value = !open.value;
  if (open.value && props.date && props.modelValue) {
    const [y, m] = props.modelValue.split("-").map(Number);
    month.value = new Date(y, m - 1, 1);
  }
}
function choose(value) {
  emit("update:modelValue", value);
  open.value = false;
  trigger.value?.focus();
}
function shift(n) {
  month.value = new Date(
    month.value.getFullYear(),
    month.value.getMonth() + n,
    1,
  );
}
function outside(e) {
  if (!root.value?.contains(e.target)) open.value = false;
}
function escape() {
  open.value = false;
  trigger.value?.focus();
}
onMounted(() => document.addEventListener("pointerdown", outside));
onBeforeUnmount(() => document.removeEventListener("pointerdown", outside));
</script>
<template>
  <div
    ref="root"
    class="glass-picker"
    :class="{ 'date-picker': date }"
    @keydown.esc.stop="escape"
    @focusout="
      (e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) open = false;
      }
    "
  >
    <label v-if="date" :for="id">{{ label }}</label
    ><button
      :id="id"
      ref="trigger"
      class="picker-trigger"
      type="button"
      :aria-label="label"
      :aria-expanded="open"
      @click="show"
    >
      <span>{{ display }}</span
      ><PhCalendarBlank v-if="date" /><PhCaretDown v-else />
    </button>
    <div
      v-if="open"
      class="picker-popup"
      :role="date ? 'dialog' : 'group'"
      :aria-label="label"
    >
      <template v-if="date"
        ><header>
          <button type="button" aria-label="上个月" @click="shift(-1)">
            <PhCaretLeft /></button
          ><strong
            >{{ month.getFullYear() }} 年 {{ month.getMonth() + 1 }} 月</strong
          ><button type="button" aria-label="下个月" @click="shift(1)">
            <PhCaretRight />
          </button>
        </header>
        <div class="calendar-grid">
          <span
            v-for="d in ['一', '二', '三', '四', '五', '六', '日']"
            :key="d"
            class="calendar-week"
            >{{ d }}</span
          ><button
            v-for="d in days"
            :key="d.value"
            type="button"
            :disabled="d.disabled"
            :aria-label="d.value"
            :aria-pressed="modelValue === d.value"
            :class="{ 'other-month': !d.current }"
            @click="choose(d.value)"
          >
            {{ d.day }}
          </button>
        </div>
        <button class="picker-clear" type="button" @click="choose('')">
          清除日期
        </button></template
      ><template v-else
        ><button
          v-for="option in options"
          :key="option.value"
          class="picker-option"
          type="button"
          :aria-pressed="modelValue === option.value"
          @click="choose(option.value)"
        >
          {{ option.label }}
        </button></template
      >
    </div>
  </div>
</template>
