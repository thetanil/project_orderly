<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "./state.svelte";

  interface Cmd { label: string; hint?: string; run: () => void }
  let q = $state("");
  let active = $state(0);
  let itemHits = $state.raw<Cmd[]>([]);
  let input: HTMLInputElement;

  const actions: Cmd[] = [
    { label: "New item", hint: "N", run: () => (app.dialog = "new") },
    { label: "Go to Tree", run: () => (app.view = "tree") },
    { label: "Go to Problems", run: () => (app.view = "problems") },
    { label: "Next problem", hint: "F8", run: () => app.nextProblem(1) },
    { label: "Undo", hint: "Ctrl+Z", run: () => app.undo() },
    { label: "Redo", hint: "Ctrl+Shift+Z", run: () => app.redo() },
    { label: "Expand all", run: () => app.expandAll() },
    { label: "Collapse all", run: () => app.collapseAll() },
    { label: "Toggle theme", run: () => app.setSetting("theme", app.settings.theme === "dark" ? "light" : "dark") },
    { label: "Toggle row density", run: () => app.setSetting("density", app.settings.density === "compact" ? "comfortable" : "compact") },
    { label: "Toggle show removed", run: () => { app.showRemoved = !app.showRemoved; app.rebuild(); } },
  ];
  const fuzzy = (needle: string, hay: string) => {
    let i = 0;
    for (const ch of hay.toLowerCase()) if (ch === needle[i]) i++;
    return i === needle.length;
  };
  const matchedActions = $derived(actions.filter((a) => !q || fuzzy(q.toLowerCase(), a.label)));
  const list = $derived([...matchedActions, ...itemHits]);

  $effect(() => {
    const query = q;
    if (!query.trim()) { itemHits = []; return; }
    app.suggest("item", query, undefined, 12).then((rs) => {
      if (query === q) itemHits = rs.map((s) => ({ label: `${s.id}  ${s.title}`, hint: s.label, run: () => app.reveal(s.id!) }));
    });
  });
  $effect(() => { q; active = 0; });
  onMount(() => input.focus());

  function run(c?: Cmd) { app.dialog = null; c?.run(); }
  function onkeydown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") { active = Math.min(list.length - 1, active + 1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(0, active - 1); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); run(list[active]); }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="overlay" onclick={() => (app.dialog = null)}>
  <div class="modal" onclick={(e) => e.stopPropagation()}>
    <input bind:this={input} bind:value={q} placeholder="Jump to an item, screen or action…" {onkeydown} style="width:100%" />
    <ul>
      {#each list as c, i}
        <li class:active={i === active} onmousedown={() => run(c)}><span>{c.label}</span><span class="muted">{c.hint ?? ""}</span></li>
      {/each}
      {#if !list.length}<li class="muted">No matches</li>{/if}
    </ul>
  </div>
</div>

<style>
  ul{list-style:none;margin:0.5rem 0 0;padding:0}
  li{display:flex;justify-content:space-between;padding:0.25rem 0.5rem;border-radius:0.1875rem;cursor:pointer}
  li.active,li:hover{background:var(--sel)}
</style>
