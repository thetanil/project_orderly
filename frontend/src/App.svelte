<script lang="ts">
  import { onMount } from "svelte";
  import { app } from "./state.svelte";
  import Tree from "./Tree.svelte";
  import Inspector from "./Inspector.svelte";
  import Problems from "./Problems.svelte";
  import Palette from "./Palette.svelte";
  import NewItem from "./NewItem.svelte";
  import Conflicts from "./Conflicts.svelte";
  import PickParent from "./PickParent.svelte";
  import MultiFilter from "./MultiFilter.svelte";

  let filterEl = $state<HTMLInputElement>();

  onMount(() => {
    const start = () => { if (!app.loaded) app.load(); };
    if (window.pywebview?.api) start();
    else window.addEventListener("pywebviewready", start);
    const fallback = setTimeout(start, 2000); // plain browser: show the "not in the window" message
    const timer = setInterval(() => app.poll(), 1500);
    return () => { clearTimeout(fallback); clearInterval(timer); };
  });

  const typed = (t: EventTarget | null) => {
    const el = t as HTMLElement | null;
    if (!el) return false;
    return ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || !!el.closest?.(".cm-editor");
  };
  const nativeText = (t: EventTarget | null) => {
    const el = t as HTMLElement | null;
    return !!el && ["INPUT", "TEXTAREA"].includes(el.tagName);
  };

  function startDrag(e: PointerEvent) {
    const el = e.currentTarget as HTMLElement;
    el.setPointerCapture(e.pointerId);
    const move = (m: PointerEvent) => app.setPaneW((window.innerWidth - m.clientX) / (16 * app.zoom));
    const up = () => { el.removeEventListener("pointermove", move); el.removeEventListener("pointerup", up); };
    el.addEventListener("pointermove", move); el.addEventListener("pointerup", up);
  }

  function onkeydown(e: KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && ["=", "+", "-", "0"].includes(e.key)) {
      e.preventDefault();
      app.setZoom(e.key === "0" ? 1 : app.zoom + (e.key === "-" ? -0.1 : 0.1));
      return;
    }
    const mod = e.ctrlKey || e.metaKey;
    if (mod && e.key.toLowerCase() === "k") { e.preventDefault(); app.dialog = app.dialog === "palette" ? null : "palette"; return; }
    if (e.key === "Escape" && app.dialog && app.dialog !== "conflicts") { app.dialog = null; return; }
    if (app.dialog) return;
    if (mod && !nativeText(e.target) && (e.key.toLowerCase() === "z" || e.key.toLowerCase() === "y")) {
      e.preventDefault();
      if (e.key.toLowerCase() === "y" || e.shiftKey) app.redo(); else app.undo();
      return;
    }
    if (e.key === "F8") { e.preventDefault(); app.nextProblem(e.shiftKey ? -1 : 1); return; }
    if (typed(e.target)) {
      if (e.key === "Escape") { (e.target as HTMLElement).blur(); document.getElementById("tree")?.focus(); }
      return;
    }
    if (e.key === "/") { e.preventDefault(); filterEl?.focus(); }
    else if (e.key.toLowerCase() === "n" && !mod && !e.altKey) { e.preventDefault(); app.dialog = "new"; }
  }

  const typeOptions = $derived(Object.entries(app.model.types).map(([v, t]) => ({ value: v, label: t.label })));
  const stateOptions = $derived(
    [...new Set(Object.values(app.model.types).flatMap((t) => Object.keys(t.states)))].map((v) => ({ value: v, label: v })),
  );
  const iterOptions = $derived(Object.values(app.iterations).map((i) => ({ value: i.id, label: i.name })));

  function statusText() {
    const s = app.status;
    const warn = s.warnings ? ` · ${s.warnings} warning${s.warnings > 1 ? "s" : ""}` : "";
    switch (s.state) {
      case "saved": return { cls: "ok", text: "✓ saved" + warn };
      case "unsaved": return { cls: "warn", text: "● unsaved" + warn };
      case "errors": return { cls: "err", text: `⛔ ${s.errors} error${s.errors > 1 ? "s" : ""} – not saved` + warn };
      case "memory": return { cls: "muted", text: "in memory only (no file) – open one with `po gui FILE`" + warn };
      case "conflicts": return { cls: "err", text: `⚠ ${s.conflicts} conflict${s.conflicts > 1 ? "s" : ""} – saving paused` + warn };
      case "external-error": return { cls: "err", text: "⚠ file changed on disk but is unreadable – saving paused" };
      case "save-failed": return { cls: "err", text: "⛔ could not save – will retry" };
      default: return { cls: "muted", text: s.state };
    }
  }
  const st = $derived((app.status, statusText()));
</script>

<svelte:window {onkeydown} />

{#if !app.loaded}
  <div class="center muted">Loading…</div>
{:else if app.error}
  <div class="center">
    <div class="errbox">
      <h2>Cannot open this backlog</h2>
      <p>{app.error}</p>
      <p class="muted">Fix the file (or run <span class="mono">po validate FILE</span>) and start Backlog Desk again.</p>
    </div>
  </div>
{:else}
  <div class="shell">
    <header>
      <strong>Backlog Desk</strong>
      <nav>
        <button class:on={app.view === "tree"} onclick={() => (app.view = "tree")}>Tree</button>
        <button class:on={app.view === "problems"} onclick={() => (app.view = "problems")}>
          Problems
          {#if app.status.errors}<span class="err">⛔{app.status.errors}</span>{/if}
          {#if app.status.warnings}<span class="warn">⚠{app.status.warnings}</span>{/if}
        </button>
      </nav>
      <button class="primary" onclick={() => (app.dialog = "new")} title="New item (N)">+ New</button>
      <button onclick={() => app.undo()} disabled={!app.canUndo} title="Undo (Ctrl+Z)">↶</button>
      <button onclick={() => app.redo()} disabled={!app.canRedo} title="Redo (Ctrl+Shift+Z)">↷</button>
      <span class="grow"></span>
      <button onclick={() => (app.dialog = "palette")} title="Command palette (Ctrl+K)">Ctrl+K</button>
      <select value={app.settings.currentUser ?? ""} onchange={(e) => app.setSetting("currentUser", e.currentTarget.value || null)} title="Who am I">
        <option value="">(me: not set)</option>
        {#each Object.values(app.people) as p}<option value={p.id}>{p.name}</option>{/each}
      </select>
      <button onclick={() => app.setZoom(app.zoom - 0.1)} title="Smaller (Ctrl+-)">A−</button>
      <button onclick={() => app.setZoom(1)} title="Reset zoom (Ctrl+0)">{Math.round(app.zoom * 100)}%</button>
      <button onclick={() => app.setZoom(app.zoom + 0.1)} title="Larger (Ctrl++)">A+</button>
      <button onclick={() => app.setSetting("density", app.settings.density === "compact" ? "comfortable" : "compact")} title="Row density">
        {app.settings.density === "compact" ? "▤" : "☰"}
      </button>
      <button onclick={() => app.setSetting("theme", app.settings.theme === "dark" ? "light" : "dark")} title="Toggle theme">
        {app.settings.theme === "dark" ? "☀" : "☾"}
      </button>
    </header>

    {#if app.view === "tree"}
      <div class="filters">
        <input bind:this={filterEl} placeholder="Filter title / id…  ( / )" style="width:15rem"
          bind:value={app.filter} oninput={() => app.rebuild()} />
        <MultiFilter label="Type" options={typeOptions} selected={app.fTypes} onchange={(s) => { app.fTypes = s; app.rebuild(); }} />
        <MultiFilter label="State" options={stateOptions} selected={app.fStates} onchange={(s) => { app.fStates = s; app.rebuild(); }} />
        <MultiFilter label="Iteration" options={iterOptions} selected={app.fIterations} onchange={(s) => { app.fIterations = s; app.rebuild(); }} />
        <label title={app.settings.currentUser ? "" : "Pick who you are (top right) to enable"}>
          <input type="checkbox" bind:checked={app.mine} disabled={!app.settings.currentUser} onchange={() => app.rebuild()} /> Mine
        </label>
        <label><input type="checkbox" bind:checked={app.showRemoved} onchange={() => app.rebuild()} /> Show removed</label>
        <button onclick={() => app.expandAll()}>Expand all</button>
        <button onclick={() => app.collapseAll()}>Collapse all</button>
      </div>
      <main style:grid-template-columns="1fr 6px {app.paneW}rem">
        <Tree />
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <div class="split" role="separator" aria-orientation="vertical" tabindex="0" title="Drag to resize (double-click to reset)"
          onpointerdown={startDrag} ondblclick={() => app.setPaneW(24)}></div>
        <Inspector />
      </main>
    {:else}
      <main class="single"><Problems /></main>
    {/if}

    <footer>
      <span class={st.cls}>{st.text}</span>
      <span>{app.rows.length} rows / {app.items.size} items</span>
      {#if app.path}<span class="muted" title={app.path}>{app.path.split(/[\\/]/).pop()}</span>{/if}
      <span class="grow"></span>
      <span class="mono">api {app.perf.api.toFixed(0)} ms · render {app.perf.render.toFixed(1)} ms</span>
    </footer>
  </div>

  {#if app.dialog === "new"}<NewItem />{/if}
  {#if app.dialog === "palette"}<Palette />{/if}
  {#if app.dialog === "conflicts"}<Conflicts />{/if}
  {#if app.dialog && typeof app.dialog === "object"}<PickParent />{/if}
  {#if app.toast}<div class="toast" role="status">{app.toast}</div>{/if}
{/if}

<style>
  .center{height:100%;display:flex;align-items:center;justify-content:center}
  .errbox{max-width:35rem;padding:1.25rem;border:1px solid var(--err);border-radius:0.5rem;background:var(--surface)}
  .errbox h2{margin-top:0;color:var(--err)}
  .shell{height:100%;display:grid;grid-template-rows:auto auto 1fr auto}
  header,.filters{display:flex;gap:0.625rem;align-items:center;padding:0.375rem 0.75rem;border-bottom:1px solid var(--border);background:var(--surface);flex-wrap:wrap}
  .filters{padding:0.25rem 0.75rem;background:var(--bg)}
  .grow{flex:1}
  nav{display:flex;gap:2px}
  nav button.on{background:var(--sel);border-color:var(--accent)}
  main{display:grid;min-height:0}
  .split{cursor:col-resize;background:var(--border);opacity:.5}
  .split:hover{background:var(--accent);opacity:1}
  main.single{grid-template-columns:1fr}
  footer{display:flex;gap:1rem;padding:0.25rem 0.75rem;border-top:1px solid var(--border);background:var(--surface);color:var(--muted);font-size:0.75rem}
  label{display:inline-flex;gap:0.25rem;align-items:center}
</style>
