<script setup lang="ts">
import { computed } from 'vue'
import { MSI_LATEST, RELEASES, SOURCE_MAIN, megabytes, useLatestRelease } from '../release'

defineProps<{ compact?: boolean }>()
const release = useLatestRelease()
const details = computed(() => {
  const r = release.value
  if (!r) return 'Windows 10 and 11, 64-bit · Free'
  return [`Version ${r.version}`, r.date, megabytes(r.msiSize), 'Windows 10 and 11, 64-bit'].filter(Boolean).join(' · ')
})
</script>

<template>
  <div class="dl" :class="{ compact }">
    <a class="dl-main" :href="release?.msiUrl ?? MSI_LATEST">
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M3 5.5 10 4.5v7H3zm8-1.15L21 3v8.5H11zM3 12.5h7v7l-7-1zm8 0h10V21l-10-1.4z" /></svg>
      <span>
        <strong>Download for Windows</strong>
        <small>Tessera-x64.msi · installer</small>
      </span>
    </a>
    <p class="dl-meta">{{ details }}</p>
    <p class="dl-links">
      <a :href="release?.sourceZip ?? SOURCE_MAIN">Source code (.zip)</a>
      <span aria-hidden="true">·</span>
      <a :href="release?.notesUrl ?? RELEASES">{{ release ? 'Release notes' : 'All releases' }}</a>
      <template v-if="release?.sumsUrl">
        <span aria-hidden="true">·</span>
        <a :href="release.sumsUrl">SHA-256 checksums</a>
      </template>
    </p>
  </div>
</template>

<style scoped>
.dl {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}

.dl-main {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 14px 26px 14px 20px;
  border-radius: 14px;
  background: var(--t-grad);
  color: #fff;
  text-decoration: none;
  box-shadow: 0 14px 34px -12px rgba(106, 92, 255, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.3);
  transition: filter 0.15s, transform 0.15s;
}

.dl-main:hover {
  filter: brightness(1.07) saturate(1.05);
  transform: translateY(-1px);
}

.dl-main span {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.25;
}

.dl-main strong {
  font-size: 17px;
}

.dl-main small {
  font-size: 12.5px;
  opacity: 0.85;
}

.dl-meta {
  margin: 0;
  color: var(--vp-c-text-2);
  font-size: 13.5px;
}

.dl-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin: 0;
  font-size: 14px;
}

.dl-links a {
  color: var(--vp-c-brand-1);
  font-weight: 500;
  text-decoration: none;
}

.dl-links a:hover {
  text-decoration: underline;
}

.dl-links span {
  color: var(--vp-c-text-3);
}
</style>
