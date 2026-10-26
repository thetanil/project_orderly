<script lang="ts">
  import { tick, untrack } from "svelte";
  import { app } from "./state.svelte";
  import type { Item } from "./types";

  let box: HTMLDivElement;
  let scrollTop = $state(0);
  let height = $state(600);
  let editing = $state<{ id: string; field: "title" | "state" | "priority" | "storyPoints" } | null>(null);
  let cancelled = false;
  let drag = $state<{ id: string; targets: Set<string> } | null>(null);
  let hover = $state<{ id: string; mode: "into" | "before" | "after" } | null>(null);

  const rowH = $derived((app.settings.density === "comfortable" ? 34 : 28) * app.zoom);
  const first = $derived(Math.max(0, Math.floor(scrollTop / rowH) - 5));
  const last = $derived(Math.min(app.rows.length, Math.ceil((scrollTop + height) / rowH) + 5));
  const visible = $derived(app.rows.slice(first, last));

  // Only a new scroll request may move the viewport; reading scrollTop/height/rowH here
  // would re-run this on every scroll and snap the tree back to the selected row.
  $effect(() => {
    const r = app.scrollRequest;
    if (!r) return;
    untrack(() => {
      const i = app.rows.findIndex((x) => x.id === r.id);
      if (i < 0) return;
      if (i * rowH < scrollTop) box.scrollTop = i * rowH;
      else if ((i + 1) * rowH > scrollTop + height) box.scrollTop = (i + 1) * rowH - height;
    });
  });

  function focusSelect(node: HTMLInputElement | HTMLSelectElement) {
    node.focus();
    if (node instanceof HTMLInputElement) node.select();
  }

  function startEdit(id: string, field: "title" | "state" | "priority" | "storyPoints") {
    const it = app.items.get(id);
    if (!it) return;
    if (field === "storyPoints" && app.type(it)?.estimation === "forbidden") return;
    app.select(id, false);
    cancelled = false;
    editing = { id, field };
  }
  async function commit(it: Item, value: string) {
    const e = editing;
    editing = null;
    if (cancelled || !e) return;
    const same = String((it as Record<string, unknown>)[e.field] ?? "") === value;
    if (!same) await app.edit(it.id, e.field, value);
    box.focus();
  }
  function editKey(e: KeyboardEvent, it: Item) {
    e.stopPropagation();
    if (e.key === "Enter") (e.currentTarget as HTMLElement).blur();
    else if (e.key === "Escape") { cancelled = true; editing = null; box.focus(); }
  }

  function onkeydown(e: KeyboardEvent) {
    if (editing) return;
    const rows = app.rows;
    const i = rows.findIndex((r) => r.id === app.current);
    const cur = i >= 0 ? rows[i] : undefined;
    const go = (n: number, extend = false) => {
      const r = rows[Math.max(0, Math.min(rows.length - 1, n))];
      if (!r) return;
      if (extend && app.anchor) app.clickRow(r.id, { shiftKey: true } as MouseEvent);
      else app.select(r.id);
      app.scrollRequest = { id: r.id, n: Math.random() };
    };
    const page = Math.max(1, Math.floor(height / rowH));
    if (e.altKey && (e.key === "ArrowUp" || e.key === "ArrowDown") && cur) { e.preventDefault(); app.moveBy(cur.id, e.key === "ArrowUp" ? -1 : 1); return; }
    switch (e.key) {
      case "ArrowDown": go(i + 1, e.shiftKey); break;
      case "ArrowUp": go(i - 1, e.shiftKey); break;
      case "PageDown": go(i + page); break;
      case "PageUp": go(i - page); break;
      case "Home": go(0); break;
      case "End": go(rows.length - 1); break;
      case "ArrowRight":
        if (!cur) break;
        if ((app.kids.get(cur.id) ?? []).length && !app.expanded.has(cur.id)) app.toggle(cur.id); else go(i + 1);
        break;
      case "ArrowLeft":
        if (!cur) break;
        if (app.expanded.has(cur.id) && (app.kids.get(cur.id) ?? []).length) app.toggle(cur.id);
        else { const p = app.items.get(cur.id)?.parent; if (p) app.select(p); }
        break;
      case "Tab":
        if (cur) app.reparentStep(cur.id, e.shiftKey ? -1 : 1);
        break;
      case "Enter": case "F2":
        if (cur) startEdit(cur.id, "title");
        break;
      case "Delete":
        if (cur && app.selected.size <= 1) e.shiftKey ? app.deleteItem(cur.id) : app.remove(cur.id);
        break;
      default: return;
    }
    e.preventDefault();
  }

  // -- drag and drop: siblings rerank, rows exactly one level above reparent --
  function dropMode(targetId: string, e: DragEvent): "into" | "before" | "after" | null {
    if (!drag || targetId === drag.id) return null;
    const d = app.items.get(drag.id)!, t = app.items.get(targetId)!;
    if ((t.parent ?? null) === (d.parent ?? null)) {
      const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
      return e.clientY - r.top < r.height / 2 ? "before" : "after";
    }
    return drag.targets.has(targetId) ? "into" : null;
  }
  function dragstart(e: DragEvent, id: string) {
    const d = app.items.get(id)!;
    const want = app.levelIndex(d) - 1;
    const targets = new Set(want < 0 ? [] : [...app.items.values()].filter((x) => app.levelIndex(x) === want && app.category(x) !== "Removed").map((x) => x.id));
    drag = { id, targets };
    e.dataTransfer?.setData("text/plain", id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
  }
  function dragover(e: DragEvent, id: string) {
    const mode = dropMode(id, e);
    if (!mode) { hover = null; return; }
    e.preventDefault();
    hover = { id, mode };
  }
  async function drop(e: DragEvent, id: string) {
    const mode = dropMode(id, e);
    const d = drag;
    drag = null; hover = null;
    if (!mode || !d) return;
    e.preventDefault();
    if (mode === "into") await app.mutate("move", d.id, id, null);
    else {
      const it = app.items.get(d.id)!;
      const sibs = app.siblings(d.id).filter((s) => s !== d.id);
      const at = sibs.indexOf(id) + (mode === "after" ? 1 : 0);
      await app.mutate("move", d.id, it.parent ?? null, at);
    }
    app.select(d.id);
  }

  function rollupTitle(it: Item) {
    const r = it.rollup!;
    return `rollup: ${r.estimatedCount} estimated, ${r.unestimatedCount} unestimated, ${r.notEstimableCount} not estimable`;
  }
  const worst = (id: string) => { const l = app.issuesFor(id); return l.find((i) => i.level === "E") ?? l[0]; };
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div id="tree" bind:this={box} bind:clientHeight={height} tabindex="0" role="tree" {onkeydown}
  onscroll={(e) => (scrollTop = e.currentTarget.scrollTop)}>
  <div class="spacer" style:height="{app.rows.length * rowH}px">
    {#each visible as r, n (r.id)}
      {@const it = app.items.get(r.id)}
      {#if it}
        {@const ty = app.type(it)}
        {@const c = app.category(it)}
        {@const bad = worst(it.id)}
        {@const has = (app.kids.get(it.id) ?? []).length > 0}
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="row" class:sel={app.selected.has(it.id)} class:cur={app.current === it.id} class:removed={c === "Removed"}
          class:target={drag?.targets.has(it.id)} class:into={hover?.id === it.id && hover.mode === "into"}
          class:before={hover?.id === it.id && hover.mode === "before"} class:after={hover?.id === it.id && hover.mode === "after"}
          style:top="{(first + n) * rowH}px" style:padding-left="{0.5 + r.depth * 1.125}rem" role="treeitem" aria-selected={app.selected.has(it.id)}
          draggable={editing === null} ondragstart={(e) => dragstart(e, it.id)} ondragend={() => { drag = null; hover = null; }}
          ondragover={(e) => dragover(e, it.id)} ondrop={(e) => drop(e, it.id)}
          onclick={(e) => app.clickRow(it.id, e)}>
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <span class="tw" role="button" tabindex="-1" onclick={(e) => { e.stopPropagation(); if (has) app.toggle(it.id); }}>
            {has ? (app.expanded.has(it.id) || app.filtering ? "▾" : "▸") : ""}
          </span>
          <span class="dot" style:background={ty?.color} title={ty?.label}></span>
          <span class="id mono">{it.id}</span>

          {#if editing?.id === it.id && editing.field === "title"}
            <input class="title-in" value={it.title} use:focusSelect onkeydown={(e) => editKey(e, it)} onblur={(e) => commit(it, e.currentTarget.value)} onclick={(e) => e.stopPropagation()} />
          {:else}
            <span class="title" role="presentation" ondblclick={() => startEdit(it.id, "title")}>{it.title}</span>
          {/if}

          {#if editing?.id === it.id && editing.field === "state"}
            <select use:focusSelect onkeydown={(e) => editKey(e, it)} onchange={(e) => e.currentTarget.blur()} onblur={(e) => commit(it, e.currentTarget.value)} onclick={(e) => e.stopPropagation()}>
              {#each Object.keys(ty.states) as s}<option selected={s === it.state}>{s}</option>{/each}
            </select>
          {:else}
            <span class="chip {c}" role="presentation" ondblclick={() => startEdit(it.id, "state")}>{it.state}</span>
          {/if}

          {#if editing?.id === it.id && editing.field === "priority"}
            <select class="num-in" use:focusSelect onkeydown={(e) => editKey(e, it)} onchange={(e) => e.currentTarget.blur()} onblur={(e) => commit(it, e.currentTarget.value)} onclick={(e) => e.stopPropagation()}>
              <option value="">–</option>
              {#each [1, 2, 3, 4] as p}<option value={p} selected={it.priority === p}>P{p}</option>{/each}
            </select>
          {:else}
            <span class="num" role="presentation" ondblclick={() => startEdit(it.id, "priority")}>{it.priority ? "P" + it.priority : ""}</span>
          {/if}

          {#if it.rollup}
            <span class="num hint" title={rollupTitle(it)}>Σ{it.rollup.storyPoints}{it.rollup.unestimatedCount ? ` +${it.rollup.unestimatedCount}?` : ""}{it.rollup.notEstimableCount ? ` ·${it.rollup.notEstimableCount}n/e` : ""}</span>
          {:else if editing?.id === it.id && editing.field === "storyPoints"}
            <input class="num-in" type="number" min="0" step="0.5" value={it.storyPoints ?? ""} use:focusSelect onkeydown={(e) => editKey(e, it)} onblur={(e) => commit(it, e.currentTarget.value)} onclick={(e) => e.stopPropagation()} />
          {:else}
            <span class="num" role="presentation" ondblclick={() => startEdit(it.id, "storyPoints")}>{it.storyPoints ?? "–"}</span>
          {/if}
          <span class="badge {bad?.level ?? ''}" title={bad ? `${bad.rule}: ${bad.message}` : ""}>{bad ? (bad.level === "E" ? "⛔" : "⚠") : ""}</span>
        </div>
      {/if}
    {/each}
  </div>
  {#if !app.rows.length}<div class="empty muted">Nothing to show{app.filtering ? " – clear the filters" : ""}.</div>{/if}
</div>

<style>
  #tree{overflow:auto;position:relative;background:var(--surface);outline:none}
  .spacer{position:relative}
  .row{position:absolute;left:0;right:0;height:var(--row);display:flex;align-items:center;gap:0.5rem;padding-right:0.75rem;white-space:nowrap;cursor:default;border-top:2px solid transparent;border-bottom:2px solid transparent}
  .row:hover{background:var(--hover)}.row.sel{background:var(--sel2)}.row.cur{background:var(--sel)}
  .row.removed .title{text-decoration:line-through;color:var(--muted)}
  .row.target{outline:1px dashed var(--accent);outline-offset:-2px}
  .row.into{background:var(--sel);outline:2px solid var(--accent)}
  .row.before{border-top-color:var(--accent)}.row.after{border-bottom-color:var(--accent)}
  .tw{width:1rem;text-align:center;color:var(--muted);flex:none;cursor:pointer}
  .id{color:var(--muted);width:7.5rem;flex:none;overflow:hidden;text-overflow:ellipsis}
  .title{flex:1;overflow:hidden;text-overflow:ellipsis}
  .title-in{flex:1;padding:0 0.25rem}
  .num{width:3.75rem;text-align:right;flex:none}.num.hint{color:var(--muted)}
  .num-in{width:4rem;flex:none;padding:0 2px}
  .badge{width:1rem;flex:none;text-align:center}.badge.E{color:var(--err)}.badge.W{color:var(--warn)}
  .empty{padding:1.5rem}
</style>
