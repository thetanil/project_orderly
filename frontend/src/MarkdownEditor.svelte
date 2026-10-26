<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { EditorState } from "@codemirror/state";
  import { EditorView, keymap, placeholder as cmPlaceholder } from "@codemirror/view";
  import { defaultKeymap } from "@codemirror/commands";
  import { markdown } from "@codemirror/lang-markdown";
  import { HighlightStyle, syntaxHighlighting } from "@codemirror/language";
  import { autocompletion, type CompletionContext } from "@codemirror/autocomplete";
  import { tags as t } from "@lezer/highlight";
  import { app } from "./state.svelte";

  let { value, field, onchange }: { value: string; field: string; onchange: (v: string) => void } = $props();

  let host: HTMLDivElement;
  let view: EditorView;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let pending: string | null = null;
  let syncing = false;

  // colours come from CSS variables, so the editor follows the app's dark/light toggle
  const theme = EditorView.theme({
    "&": { color: "var(--text)", backgroundColor: "var(--surface)", border: "1px solid var(--border)", borderRadius: "4px", maxHeight: "320px" },
    "&.cm-focused": { outline: "2px solid var(--accent)", outlineOffset: "-1px" },
    ".cm-content": { caretColor: "var(--text)", fontFamily: "ui-monospace, Consolas, monospace", fontSize: "12px", padding: "4px 0" },
    ".cm-cursor": { borderLeftColor: "var(--text)" },
    ".cm-scroller": { overflow: "auto" },
    ".cm-selectionBackground, &.cm-focused .cm-selectionBackground": { background: "var(--sel)" },
    ".cm-tooltip": { background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" },
    ".cm-tooltip-autocomplete ul li[aria-selected]": { background: "var(--sel)", color: "var(--text)" },
  });
  const highlight = HighlightStyle.define([
    { tag: t.heading, color: "var(--accent)", fontWeight: "bold" },
    { tag: t.strong, fontWeight: "bold" },
    { tag: t.emphasis, fontStyle: "italic" },
    { tag: [t.link, t.url], color: "var(--accent)" },
    { tag: t.monospace, color: "var(--warn)" },
    { tag: t.quote, color: "var(--muted)" },
    { tag: t.processingInstruction, color: "var(--muted)" },
  ]);

  async function complete(ctx: CompletionContext) {
    const m = ctx.matchBefore(/[#@][\w.-]*/);
    if (!m || (m.from === m.to - 0 && !ctx.explicit && m.text.length < 1)) return null;
    const sigil = m.text[0], q = m.text.slice(1);
    const res = await app.suggest(sigil === "#" ? "item" : "person", q, undefined, 12);
    return {
      from: m.from,
      filter: false,
      options: res.map((s) => ({
        label: sigil + (s.id ?? ""),
        detail: s.title ?? s.name ?? "",
        apply: sigil + (s.id ?? ""),
      })),
    };
  }

  function emit() {
    clearTimeout(timer);
    if (pending !== null) {
      const v = pending;
      pending = null;
      onchange(v);
    }
  }

  onMount(() => {
    view = new EditorView({
      parent: host,
      state: EditorState.create({
        doc: value ?? "",
        extensions: [
          // no history(): undo/redo is the app-level one, so editor edits share a single undo stack
          keymap.of(defaultKeymap),
          markdown(),
          EditorView.lineWrapping,
          theme,
          syntaxHighlighting(highlight),
          autocompletion({ override: [complete], activateOnTyping: true }),
          cmPlaceholder("Markdown (GFM). # for items, @ for people"),
          EditorView.updateListener.of((u) => {
            if (!u.docChanged || syncing) return;
            pending = u.state.doc.toString();
            clearTimeout(timer);
            timer = setTimeout(emit, 500);
          }),
          EditorView.domEventHandlers({ blur: () => { emit(); return false; } }),
        ],
      }),
    });
    host.dataset.field = field;
    app.flushers.add(emit);
  });

  onDestroy(() => { emit(); app.flushers.delete(emit); view?.destroy(); });

  // external changes (undo, merge, quick fix) replace the document
  $effect(() => {
    const v = value ?? "";
    if (view && pending === null && v !== view.state.doc.toString()) {
      syncing = true;
      view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: v } });
      syncing = false;
    }
  });
</script>

<div class="md" bind:this={host} data-field={field}></div>
