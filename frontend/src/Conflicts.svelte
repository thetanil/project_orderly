<script lang="ts">
  import { app } from "./state.svelte";

  const show = (v: unknown) => (v === null || v === undefined ? "(deleted / empty)" : typeof v === "string" ? v : JSON.stringify(v));
  const resolve = (c: { itemId: string; field: string | null }, choice: "mine" | "theirs") =>
    app.mutate("resolve_conflict", c.itemId, c.field, choice);
</script>

<div class="overlay">
  <div class="modal" style="width:min(45rem,94vw)">
    <h2>The file changed on disk</h2>
    <p class="muted">Everything else was merged. These fields were changed on both sides. Saving is paused until each is resolved.</p>
    {#each app.conflicts as c}
      <div class="c">
        <div><b class="mono">{c.itemId}</b> · <span class="mono">{c.field ?? "whole item"}</span></div>
        <div class="cols">
          <div><div class="muted">Mine</div><pre>{show(c.mine)}</pre><button onclick={() => resolve(c, "mine")}>Keep mine</button></div>
          <div><div class="muted">Theirs (disk)</div><pre>{show(c.theirs)}</pre><button onclick={() => resolve(c, "theirs")}>Take theirs</button></div>
        </div>
      </div>
    {/each}
    <div class="actions"><button onclick={() => (app.dialog = null)}>Decide later</button></div>
  </div>
</div>

<style>
  .c{border-top:1px solid var(--border);padding:0.5rem 0}
  .cols{display:grid;grid-template-columns:1fr 1fr;gap:0.75rem}
  pre{white-space:pre-wrap;word-break:break-word;background:var(--bg);padding:0.375rem;border-radius:0.25rem;max-height:7.5rem;overflow:auto;margin:2px 0 0.375rem}
</style>
