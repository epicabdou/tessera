<script setup lang="ts">
// Claims about web-based tools are kept general and hedged on purpose: we describe how
// online processing works, not any one company's plans or features.
const rows = [
  { what: 'Where your files are processed', tilepress: 'On your PC', web: 'Uploaded to the service’s servers' },
  { what: 'Works without internet', tilepress: 'Yes', web: 'No' },
  { what: 'File size and batch limits', tilepress: 'Only your PC’s', web: 'Often capped on free plans' },
  { what: 'Price', tilepress: 'Free, no ads, no account', web: 'Usually a free tier plus a subscription' },
  { what: 'Source code', tilepress: 'Open (GNU GPL v3)', web: 'Closed' },
  { what: 'Runs on', tilepress: 'Windows 10 and 11', web: 'Any device with a browser' },
]
</script>

<template>
  <div class="compare">
    <table>
      <thead>
        <tr>
          <th scope="col"></th>
          <th scope="col" class="us">Tilepress</th>
          <th scope="col">Online PDF and image sites</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.what">
          <th scope="row">{{ r.what }}</th>
          <td class="us">{{ r.tilepress }}</td>
          <td>{{ r.web }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.compare {
  overflow-x: auto;
  border: 1px solid var(--vp-c-divider);
  border-radius: 14px;
}

table {
  display: table; /* VitePress's base styles make tables blocks */
  width: 100%;
  margin: 0;
  border-collapse: collapse;
  font-size: 15px;
}

tr {
  background: none;
}

th,
td {
  padding: 13px 18px;
  border-bottom: 1px solid var(--vp-c-divider);
  text-align: left;
  vertical-align: top;
}

tbody tr:last-child th,
tbody tr:last-child td {
  border-bottom: 0;
}

thead th {
  color: var(--vp-c-text-2);
  font-size: 13px;
  font-weight: 600;
}

tbody th {
  font-weight: 500;
  color: var(--vp-c-text-2);
  width: 32%;
}

.us {
  background: var(--vp-c-brand-soft);
  color: var(--vp-c-text-1);
  font-weight: 600;
}

thead .us {
  color: var(--vp-c-brand-1);
}
</style>
