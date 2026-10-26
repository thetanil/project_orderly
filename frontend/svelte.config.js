import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

// Desktop tool: labels sit visually next to composite controls (pickers, editors), so the
// "label must wrap/point at a control" and click-handler a11y hints are noise here.
const quiet = new Set(["a11y_label_has_associated_control", "a11y_click_events_have_key_events", "a11y_interactive_supports_focus", "a11y_no_noninteractive_element_interactions"]);

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {},
  onwarn: undefined,
  vitePlugin: {},
  warningFilter: (w) => !quiet.has(w.code),
};
