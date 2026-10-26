<script lang="ts">
  import { app } from "./state.svelte";
  import Picker from "./Picker.svelte";

  const d = $derived(typeof app.dialog === "object" && app.dialog ? app.dialog : null);
  const it = $derived(d ? app.items.get(d.pickParent) : undefined);

  async function choose(id: string | undefined) {
    if (!d || !id) return;
    const r = await app.mutate("quick_fix", "R4", d.pickParent, "parent", { parent: id }).then(async (x) => (x.ok ? x : app.mutate("quick_fix", "R5", d!.pickParent, "parent", { parent: id })));
    if (r.ok) app.dialog = null;
  }
</script>

{#if d && it}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="overlay" onclick={() => (app.dialog = null)}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>Choose a parent for {it.id}</h2>
      <p class="muted">Only items exactly one level above a {app.type(it)?.label} are offered.</p>
      <Picker kind="item" forType={it.type} placeholder="Search parents…" allowClear={false} onpick={(s) => choose(s?.id)} />
      <div class="actions"><button onclick={() => (app.dialog = null)}>Cancel</button></div>
    </div>
  </div>
{/if}
