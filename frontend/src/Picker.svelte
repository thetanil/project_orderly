<script lang="ts">
  import { app } from "./state.svelte";
  import type { Suggestion } from "./types";

  let { kind, forType, value = "", placeholder = "", field, onpick, allowClear = true, free = false }: {
    kind: "item" | "person" | "iteration" | "tag";
    forType?: string;
    value?: string;
    placeholder?: string;
    field?: string;
    onpick: (s: Suggestion | null) => void;
    allowClear?: boolean;
    free?: boolean;
  } = $props();

  let text = $state("");
  let open = $state(false);
  let results = $state.raw<Suggestion[]>([]);
  let active = $state(0);
  let typing = false;

  $effect(() => { if (!typing) text = value; });

  const label = (s: Suggestion) => (s.tag ?? s.title ?? s.name ?? s.id ?? "");
  const sub = (s: Suggestion) => (s.tag ? `${s.count}×` : s.id && (s.title || s.name) ? s.id : (s.path ?? ""));

  async function search() {
    results = await app.suggest(kind, text, forType);
    active = 0;
  }
  function pick(s: Suggestion | null) {
    open = false; typing = false; text = value;
    onpick(s);
  }
  function onkeydown(e: KeyboardEvent) {
    if (e.key === "ArrowDown") { active = Math.min(results.length - 1, active + 1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(0, active - 1); e.preventDefault(); }
    else if (e.key === "Enter" && open && results[active]) { e.preventDefault(); e.stopPropagation(); pick(results[active]); }
    else if (e.key === "Enter" && free && text.trim()) { e.preventDefault(); pick({ tag: text.trim() }); }
    else if (e.key === "Enter" && !text && allowClear) { pick(null); }
    else if (e.key === "Escape" && open) { e.stopPropagation(); open = false; typing = false; text = value; }
  }
</script>

<span class="picker">
  <input data-field={field} bind:value={text} {placeholder} autocomplete="off"
    onfocus={() => { open = true; search(); }}
    oninput={() => { typing = true; open = true; search(); }}
    onblur={() => setTimeout(() => { open = false; typing = false; text = value; }, 120)}
    {onkeydown} />
  {#if open && results.length}
    <ul>
      {#each results as s, i}
        <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
        <li class:active={i === active} onmousedown={(e) => { e.preventDefault(); pick(s); }}>
          <span>{label(s)}</span><span class="muted mono">{sub(s)}</span>
        </li>
      {/each}
    </ul>
  {/if}
</span>

<style>
  .picker{position:relative;display:block}
  input{width:100%}
  ul{position:absolute;z-index:8;left:0;right:0;top:100%;margin:2px 0 0;padding:2px;list-style:none;background:var(--surface);border:1px solid var(--border);border-radius:4px;box-shadow:var(--shadow);max-height:240px;overflow:auto}
  li{display:flex;justify-content:space-between;gap:10px;padding:3px 6px;cursor:pointer;border-radius:3px}
  li.active,li:hover{background:var(--sel)}
</style>
