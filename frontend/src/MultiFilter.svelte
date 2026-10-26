<script lang="ts">
  let { label, options, selected, onchange }: {
    label: string;
    options: { value: string; label: string }[];
    selected: Set<string>;
    onchange: (s: Set<string>) => void;
  } = $props();
  let open = $state(false);

  function toggle(v: string) {
    const s = new Set(selected);
    s.has(v) ? s.delete(v) : s.add(v);
    onchange(s);
  }
</script>

<span class="wrap">
  <button class:active={selected.size > 0} onclick={() => (open = !open)} aria-expanded={open}>
    {label}{selected.size ? ` (${selected.size})` : ""} ▾
  </button>
  {#if open}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="pop" onmouseleave={() => (open = false)}>
      {#each options as o}
        <label><input type="checkbox" checked={selected.has(o.value)} onchange={() => toggle(o.value)} /> {o.label}</label>
      {/each}
      {#if selected.size}<button class="link" onclick={() => onchange(new Set())}>clear</button>{/if}
    </div>
  {/if}
</span>

<style>
  .wrap{position:relative}
  .active{border-color:var(--accent);background:var(--sel)}
  .pop{position:absolute;top:100%;left:0;z-index:5;background:var(--surface);border:1px solid var(--border);border-radius:4px;padding:6px 10px;min-width:150px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:3px}
  label{display:flex;gap:6px;align-items:center;white-space:nowrap}
</style>
