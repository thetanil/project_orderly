<script lang="ts">
  import { onMount } from "svelte";
  import { app, LEVELS } from "./state.svelte";
  import Picker from "./Picker.svelte";

  const types = $derived(Object.entries(app.model.types));
  let type = $state(Object.keys(app.model.types).find((t) => app.model.types[t].level === "feature") ?? Object.keys(app.model.types)[0]);
  let title = $state("");
  let parent = $state<string | null>(null);
  let key = $state("");
  let keyEdited = $state(false);
  let error = $state("");
  let titleEl: HTMLInputElement;

  const needsParent = $derived(LEVELS.indexOf(app.model.types[type]?.level) > 0);
  const parentLabel = $derived(parent ? `${parent} ${app.items.get(parent)?.title ?? ""}` : "");

  // default parent: the current item, or its nearest ancestor, that is exactly one level above
  $effect(() => {
    const want = LEVELS.indexOf(app.model.types[type]?.level) - 1;
    let cur = app.current ? app.items.get(app.current) : undefined;
    parent = null;
    while (cur) {
      if (app.levelIndex(cur) === want) { parent = cur.id; break; }
      cur = cur.parent ? app.items.get(cur.parent) : undefined;
    }
  });
  $effect(() => {
    const t = title;
    if (keyEdited) return;
    app.call("suggest_key", t || "item").then((r) => { if (!keyEdited && t === title) key = r.key; });
  });
  onMount(() => titleEl.focus());

  async function create() {
    error = "";
    const r = await app.mutate("create", type, title, needsParent ? parent : null, key || null);
    if (r.ok) app.dialog = null;
    else error = r.error;
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="overlay" onclick={() => (app.dialog = null)}>
  <div class="modal" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.key === "Enter" && !(e.target as HTMLElement).closest("ul") && create()}>
    <h2>New item</h2>
    <div class="field"><label for="n-type">Type</label>
      <select id="n-type" bind:value={type}>{#each types as [k, t]}<option value={k}>{t.label}</option>{/each}</select></div>
    <div class="field"><label for="n-title">Title</label><input id="n-title" bind:this={titleEl} bind:value={title} /></div>
    {#if needsParent}
      <div class="field"><label>Parent (one level above)</label>
        {#key type}<Picker kind="item" forType={type} value={parentLabel} placeholder="Choose a parent…" allowClear={false} onpick={(s) => (parent = s?.id ?? null)} />{/key}</div>
    {/if}
    <div class="field"><label for="n-key">Key (fixed after creation)</label>
      <input id="n-key" class="mono" bind:value={key} oninput={() => (keyEdited = true)} /></div>
    {#if error}<div class="err-text">{error}</div>{/if}
    <div class="actions">
      <button onclick={() => (app.dialog = null)}>Cancel</button>
      <button class="primary" onclick={create} disabled={!title.trim()}>Create</button>
    </div>
  </div>
</div>
