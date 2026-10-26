<script lang="ts">
  import { tick } from "svelte";
  import { app } from "./state.svelte";
  import Picker from "./Picker.svelte";
  import MarkdownEditor from "./MarkdownEditor.svelte";
  import type { Item } from "./types";

  const it = $derived(app.item);
  const ty = $derived(it ? app.type(it) : undefined);
  const issues = (f: string) => (it ? app.issuesFor(it.id).filter((i) => i.field === f) : []);
  const other = $derived(it ? app.issuesFor(it.id).filter((i) => !i.field || !["title", "state", "priority", "storyPoints", "iteration", "assignedTo", "tags", "description", "acceptanceCriteria", "localNotes", "parent"].includes(i.field)) : []);
  const catOf = (s: string) => ty?.states[s] ?? "Proposed";
  const synced = $derived(!!it?.remotes && Object.keys(it.remotes).length > 0);

  $effect(() => {
    const r = app.focusRequest;
    if (!r) return;
    tick().then(() => document.querySelector<HTMLElement>(`aside [data-field="${r.field}"]`)?.focus());
  });

  function set(field: string, value: unknown) { if (it) app.edit(it.id, field, value); }
  const persons = $derived(it?.assignedTo ? (app.people[it.assignedTo]?.name ?? it.assignedTo) : "");
  const parentText = $derived(it?.parent ? `${it.parent} ${app.items.get(it.parent)?.title ?? ""}` : "");

  async function addTag(tag: string) {
    if (!it || !tag.trim()) return;
    set("tags", [...(it.tags ?? []), tag.trim()]);
  }

  // -- bulk ------------------------------------------------------------
  let bulkTags = $state("");
  let bulkMode = $state("add");
  const bulk = (field: string, value: unknown, mode?: string) => app.mutate("bulk_set", [...app.selected], field, value, mode ?? null);
  const allStates = $derived([...new Set(Object.values(app.model.types).flatMap((t) => Object.keys(t.states)))]);
</script>

<aside>
  {#if app.selected.size > 1}
    <h2>{app.selected.size} items selected</h2>
    <p class="muted">Applies to every selected item that allows the value; others are skipped and reported. One undo step.</p>
    <div class="field"><label for="b-state">State</label>
      <select id="b-state" onchange={(e) => { if (e.currentTarget.value) bulk("state", e.currentTarget.value); e.currentTarget.value = ""; }}>
        <option value="">Set state…</option>{#each allStates as s}<option>{s}</option>{/each}
      </select></div>
    <div class="field"><label for="b-prio">Priority</label>
      <select id="b-prio" onchange={(e) => { const v = e.currentTarget.value; if (v !== "-") bulk("priority", v === "none" ? null : Number(v)); e.currentTarget.value = "-"; }}>
        <option value="-">Set priority…</option><option value="none">none</option>{#each [1, 2, 3, 4] as p}<option value={p}>P{p}</option>{/each}
      </select></div>
    <div class="field"><label>Iteration</label>
      <Picker kind="iteration" placeholder="Set iteration…" onpick={(s) => bulk("iteration", s?.id ?? null)} /></div>
    <div class="field"><label>Assignee</label>
      <Picker kind="person" placeholder="Assign to…" onpick={(s) => bulk("assignedTo", s?.id ?? null)} /></div>
    <div class="field"><label for="b-tags">Tags</label>
      <div class="row">
        <select bind:value={bulkMode}><option value="add">add</option><option value="remove">remove</option><option value="set">set</option></select>
        <input id="b-tags" bind:value={bulkTags} placeholder="comma separated" />
        <button onclick={() => { bulk("tags", bulkTags.split(",").map((x) => x.trim()).filter(Boolean), bulkMode); bulkTags = ""; }}>Apply</button>
      </div></div>
  {:else if it && ty}
    <h2><span class="dot" style:background={ty.color}></span> {ty.label} <span class="mono muted">{it.id}</span></h2>

    <div class="field"><label for="f-title">Title *</label>
      <input id="f-title" data-field="title" value={it.title} onchange={(e) => set("title", e.currentTarget.value)} />
      {#each issues("title") as i}<div class="err-text">{i.rule}: {i.message}</div>{/each}</div>

    <div class="field"><label for="f-state">State *</label>
      <div class="row"><span class="chip {catOf(it.state)}">{catOf(it.state)}</span>
        <select id="f-state" data-field="state" value={it.state} onchange={(e) => set("state", e.currentTarget.value)}>
          {#each Object.keys(ty.states) as s}<option value={s} class="o-{ty.states[s]}">{s} · {ty.states[s]}</option>{/each}
        </select></div>
      {#each issues("state") as i}<div class="err-text">{i.rule}: {i.message}</div>{/each}</div>

    <div class="field"><label for="f-prio">Priority{ty.priority === "required" ? " *" : ""}</label>
      <select id="f-prio" data-field="priority" value={String(it.priority ?? "")} onchange={(e) => set("priority", e.currentTarget.value)}>
        <option value="">–</option>{#each [1, 2, 3, 4] as p}<option value={String(p)}>P{p}</option>{/each}
      </select>
      {#each issues("priority") as i}<div class="err-text">{i.rule}: {i.message}</div>{/each}</div>

    {#if ty.estimation === "forbidden"}
      {#if it.rollup}<div class="field"><label>Effort (rollup, derived)</label>
        <div>Σ {it.rollup.storyPoints} <span class="muted">({it.rollup.estimatedCount} estimated, {it.rollup.unestimatedCount} unestimated, {it.rollup.notEstimableCount} not estimable)</span></div></div>{/if}
      {#each issues("storyPoints") as i}<div class="err-text">{i.rule}: {i.message}</div>{/each}
    {:else}
      <div class="field"><label for="f-sp">Story points{ty.estimation === "required" ? " *" : ""}</label>
        <input id="f-sp" data-field="storyPoints" type="number" min="0" step="0.5" value={it.storyPoints ?? ""} onchange={(e) => set("storyPoints", e.currentTarget.value)} />
        {#each issues("storyPoints") as i}<div class={i.level === "E" ? "err-text" : "warn-text"}>{i.rule}: {i.message}</div>{/each}</div>
    {/if}

    {#if ty.level !== "businessEpic"}
      <div class="field"><label>Parent</label>
        <Picker kind="item" forType={it.type} value={parentText} field="parent" placeholder="Choose a parent…" allowClear={false}
          onpick={(s) => s?.id && app.mutate("move", it.id, s.id, null)} />
        {#each issues("parent") as i}<div class={i.level === "E" ? "err-text" : "warn-text"}>{i.rule}: {i.message}</div>{/each}</div>
    {/if}

    <div class="field"><label>Iteration</label>
      <Picker kind="iteration" field="iteration" value={it.iteration ? (app.iterations[it.iteration]?.name ?? it.iteration) : ""} placeholder="–" onpick={(s) => set("iteration", s?.id ?? null)} />
      {#each issues("iteration") as i}<div class="err-text">{i.rule}: {i.message}</div>{/each}</div>

    <div class="field"><label>Assigned to</label>
      <Picker kind="person" field="assignedTo" value={persons} placeholder="–" onpick={(s) => set("assignedTo", s?.id ?? null)} /></div>

    <div class="field"><label>Tags</label>
      <div class="tags">
        {#each it.tags ?? [] as tg}<span class="chip">{tg} <button class="link" title="remove" onclick={() => set("tags", (it.tags ?? []).filter((x) => x !== tg))}>×</button></span>{/each}
      </div>
      <Picker kind="tag" field="tags" placeholder="add tag (Enter)…" allowClear={false} free
        onpick={(s) => { if (s?.tag) addTag(s.tag); }} /></div>

    <div class="field"><label>Description</label>
      {#key it.id}<MarkdownEditor field="description" value={it.description ?? ""} onchange={(v) => set("description", v)} />{/key}
      {#each issues("description") as i}<div class="warn-text">{i.rule}: {i.message}</div>{/each}</div>
    <div class="field"><label>Acceptance criteria</label>
      {#key it.id}<MarkdownEditor field="acceptanceCriteria" value={it.acceptanceCriteria ?? ""} onchange={(v) => set("acceptanceCriteria", v)} />{/key}
      {#each issues("acceptanceCriteria") as i}<div class="warn-text">{i.rule}: {i.message}</div>{/each}</div>
    <div class="field"><label>Local notes (never synced)</label>
      {#key it.id}<MarkdownEditor field="localNotes" value={it.localNotes ?? ""} onchange={(v) => set("localNotes", v)} />{/key}
      {#each issues("localNotes") as i}<div class="warn-text">{i.rule}: {i.message}</div>{/each}</div>

    {#if it.remotes}<div class="field"><label>Remotes (sync-owned, read-only)</label><pre class="mono ro">{JSON.stringify(it.remotes, null, 1)}</pre></div>{/if}
    {#if it.rollup}<div class="field"><label>Rollup (derived, read-only)</label><pre class="mono ro">{JSON.stringify(it.rollup)}</pre></div>{/if}

    {#each other as i}<div class="issue {i.level}"><b>{i.rule}</b> {i.field ? i.field + ": " : ""}{i.message}</div>{/each}

    <div class="actions" style="justify-content:flex-start">
      <button onclick={() => app.remove(it.id)} disabled={app.category(it) === "Removed"}>Remove</button>
      {#if !synced}<button onclick={() => app.deleteItem(it.id)}>Delete…</button>{/if}
    </div>
  {:else}
    <div class="empty muted">Select an item.</div>
  {/if}
</aside>

<style>
  aside{border-left:1px solid var(--border);padding:12px;overflow:auto;background:var(--bg)}
  h2{font-size:15px;margin:0 0 8px;display:flex;gap:6px;align-items:center}
  .row{display:flex;gap:6px;align-items:center}
  .row select{flex:1}
  .tags{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:4px}
  .ro{margin:0;padding:6px;background:var(--surface);border:1px solid var(--border);border-radius:4px;white-space:pre-wrap;color:var(--muted)}
  .issue{margin-top:8px;padding:4px 8px;border-left:3px solid var(--warn);background:var(--surface)}.issue.E{border-color:var(--err)}
  .empty{padding:24px 0}
  .o-InProgress{color:#60A5FA}.o-Resolved{color:#2DD4BF}.o-Completed{color:#4ADE80}.o-Removed{color:#A1A1AA}
</style>
