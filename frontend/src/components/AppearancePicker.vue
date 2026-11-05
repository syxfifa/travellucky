<template>
  <div class="appearance-wrap">
    <button class="appearance-trigger" type="button" :aria-expanded="open" aria-controls="appearance-panel" @click="open = !open">
      <span aria-hidden="true">◐</span><span>{{ t('appearance.title') }}</span>
    </button>
    <div v-if="open" id="appearance-panel" class="appearance-panel" role="dialog" :aria-label="t('appearance.title')">
      <div class="appearance-head"><strong>{{ t('appearance.title') }}</strong><button type="button" class="appearance-close" :aria-label="t('appearance.close')" @click="open = false">×</button></div>
      <fieldset><legend>{{ t('appearance.theme') }}</legend><div class="appearance-options"><button v-for="item in themes" :key="item.value" type="button" :aria-pressed="value.theme === item.value" @click="set('theme', item.value)">{{ t(item.label) }}</button></div></fieldset>
      <fieldset><legend>{{ t('appearance.material') }}</legend><div class="appearance-options"><button v-for="item in materials" :key="item.value" type="button" :aria-pressed="value.material === item.value" @click="set('material', item.value)">{{ t(item.label) }}</button></div></fieldset>
      <fieldset><legend>{{ t('appearance.color') }}</legend><div class="appearance-options swatches"><button v-for="item in colors" :key="item.value" type="button" :aria-label="t(item.label)" :title="t(item.label)" :aria-pressed="value.color === item.value" :style="{ '--swatch': item.swatch }" @click="set('color', item.value)"><span></span></button></div></fieldset>
      <fieldset><legend>{{ t('appearance.corner') }}</legend><div class="appearance-options"><button v-for="item in corners" :key="item.value" type="button" :aria-pressed="value.corner === item.value" @click="set('corner', item.value)">{{ t(item.label) }}</button></div></fieldset>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

type Dimension = 'theme' | 'material' | 'color' | 'corner'
const { t } = useI18n()
const open = ref(false)
const value = reactive<Record<Dimension, string>>({ theme: 'light', material: 'soft', color: 'blue', corner: 'default' })
const themes = [{ value: 'light', label: 'appearance.light' }, { value: 'dark', label: 'appearance.dark' }]
const materials = [{ value: 'soft', label: 'appearance.soft' }, { value: 'clear', label: 'appearance.clear' }, { value: 'glass', label: 'appearance.glass' }, { value: 'gradient', label: 'appearance.gradient' }]
const colors = [{ value: 'blue', label: 'appearance.blue', swatch: '#4c7fe8' }, { value: 'mint', label: 'appearance.mint', swatch: '#1c9d8a' }, { value: 'violet', label: 'appearance.violet', swatch: '#8460c9' }, { value: 'sunset', label: 'appearance.sunset', swatch: '#d87554' }]
const corners = [{ value: 'tight', label: 'appearance.tight' }, { value: 'default', label: 'appearance.default' }, { value: 'round', label: 'appearance.round' }]
const allowed: Record<Dimension, string[]> = { theme: themes.map(x => x.value), material: materials.map(x => x.value), color: colors.map(x => x.value), corner: corners.map(x => x.value) }
const dimensions: Dimension[] = ['theme', 'material', 'color', 'corner']
const apply = () => { for (const key of dimensions) document.documentElement.dataset[key] = value[key] }
const set = (key: Dimension, next: string) => { if (!allowed[key].includes(next)) return; value[key] = next; try { localStorage.setItem(`travellucky-${key}`, next) } catch {} apply() }
const restore = () => { for (const key of dimensions) { let saved = ''; try { saved = localStorage.getItem(`travellucky-${key}`) || '' } catch {} if (allowed[key].includes(saved)) value[key] = saved } apply() }
const onStorage = (event: StorageEvent) => { if (event.key?.startsWith('travellucky-')) restore() }
const onKeydown = (event: KeyboardEvent) => { if (event.key === 'Escape') open.value = false }
onMounted(() => { restore(); window.addEventListener('storage', onStorage); window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('storage', onStorage); window.removeEventListener('keydown', onKeydown) })
</script>

