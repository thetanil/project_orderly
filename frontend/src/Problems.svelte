<script lang="ts">
  import { app } from "./state.svelte";
  import type { Issue } from "./types";

  let rule = $state("");
  let level = $state("");
  const rules = $derived([...new Set(app.issues.map((i) => i.rule))].sort());
  const shown = $derived(app.issues.filter((i) => (!rule || i.rule === rule) && (!level || i.level === level)));

  function jump(i: Issue) {
    if (i.itemId && app.items.has(i.itemId)) app.focusField(i.itemId, i.field ?? "title");
    else app.say(i.itemId ? `${i.itemId} is not in the tree` : "No item for this problem.");
  }
  async function fix(i: Issue) {
    if (!i.itemId) return;
    const r = await app.mutate("quick_fix", i.rule, i.itemId, i.field);
    if (r.ui === "pick-parent") app.dialog = { pickParent: i.itemId, candidates: r.candidates };
    else if (r.ui === "focus-field") app.focusField(r.itemId, r.field);
  }
</script>

<section>
  <div class="bar">
    <select bind:value={rule}><option value="">All rules</option>{#each rules as r}<option>{r}</option>{/each}</select>
    <select bind:value={level}><option value="">All levels</option><option value="E">Errors</option><option value="W">Warnings</option></select>
    <span class="muted">{shown.length} of {app.issues.length} · F8 jumps to the next problem</span>
  </div>
  {#if !shown.length}
    <div class="empty ok">✓ {app.issues.length ? "No problems match the filter." : "No problems."}</div>
  {:else}
    <table>
      <thead><tr><th></th><th>Rule</th><th>Item</th><th>Field</th><th>Message</th><th></th></tr></thead>
      <tbody>
        {#each shown as i}
          <tr onclick={() => jump(i)}>
            <td class={i.level === "E" ? "err" : "warn"}>{i.level === "E" ? "⛔" : "⚠"}</td>
            <td class="mono">{i.rule}</td>
            <td class="mono">{i.itemId ?? ""}</td>
            <td class="mono">{i.field ?? ""}</td>
            <td>{i.message}</td>
            <td>{#if i.fix}<button onclick={(e) => { e.stopPropagation(); fix(i); }}>Fix</button>{/if}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</section>

<style>
  section{overflow:auto;background:var(--surface)}
  .bar{display:flex;gap:10px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--surface)}
  table{width:100%;border-collapse:collapse}
  th{text-align:left;color:var(--muted);font-weight:normal;padding:4px 10px;border-bottom:1px solid var(--border)}
  td{padding:4px 10px;border-bottom:1px solid var(--border)}
  tbody tr{cursor:pointer}tbody tr:hover{background:var(--hover)}
  .empty{padding:24px}
</style>
