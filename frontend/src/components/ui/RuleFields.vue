<script setup>
import { computed } from 'vue';
const props=defineProps({modelValue:{},label:{type:String,default:''}});
const emit=defineEmits(['update:modelValue']);
const names={play:'播放量',interact:'互动率',jump_3s:'3s跳出率',progress:'平均播放进度',convert:'播转粉率',difficulty:'制作难度',efficiency:'时效情况',traffic_ratio:'投流比例',lower:'扣分起始比例',upper:'高额扣分比例',middle_penalty:'中档扣分',high_penalty:'高档扣分',tag:'榜单名称',score:'分值'};
const object=computed(()=>props.modelValue!==null && typeof props.modelValue==='object');
function update(key,value){const copy=Array.isArray(props.modelValue)?[...props.modelValue]:{...props.modelValue};copy[key]=value;emit('update:modelValue',copy);}
</script>
<template><fieldset v-if="object" class="rule-fields"><legend>{{label}}</legend><RuleFields v-for="(value,key) in modelValue" :key="key" :label="Array.isArray(modelValue) ? (modelValue.length===5 ? ['P10','P25','P50','P75','P95'][key] : `第 ${Number(key)+1} 项`) : names[key] || key" :model-value="value" @update:model-value="update(key,$event)" /></fieldset><label v-else class="rule-field">{{label}}<input v-if="typeof modelValue==='number'" type="number" step="any" :value="modelValue" required @input="emit('update:modelValue',$event.target.value===''?null:Number($event.target.value))"><input v-else :value="modelValue ?? ''" @input="emit('update:modelValue',$event.target.value || null)"></label></template>
