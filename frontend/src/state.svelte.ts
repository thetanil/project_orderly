import type { Conflict, Issue, Item, Iteration, Model, Person, Resp, Row, Settings, Status, Suggestion } from "./types";

export const LEVELS = ["businessEpic", "programObjective", "feature", "workItem"];
const EMPTY_STATUS: Status = { state: "saved", errors: 0, warnings: 0, conflicts: 0, message: null };

/** All frontend state. The backend owns the data; this is only a view plus view state. */
export class AppState {
  loaded = $state(false);
  error = $state<string | null>(null);
  path = $state<string | null>(null);
  model = $state.raw<Model>({ types: {} });
  people = $state.raw<Record<string, Person>>({});
  iterations = $state.raw<Record<string, Iteration>>({});
  items = $state.raw(new Map<string, Item>());
  kids = $state.raw(new Map<string | null, string[]>());
  issues = $state.raw<Issue[]>([]);
  issuesBy = $state.raw(new Map<string, Issue[]>());
  status = $state.raw<Status>(EMPTY_STATUS);
  conflicts = $state.raw<Conflict[]>([]);
  canUndo = $state(false);
  canRedo = $state(false);
  settings = $state.raw<Settings>({ currentUser: null, theme: "dark", density: "compact" });

  view = $state<"tree" | "problems">("tree");
  filter = $state("");
  fTypes = $state.raw(new Set<string>());
  fStates = $state.raw(new Set<string>());
  fIterations = $state.raw(new Set<string>());
  mine = $state(false);
  showRemoved = $state(false);
  expanded = $state.raw(new Set<string>());
  rows = $state.raw<Row[]>([]);
  selected = $state.raw(new Set<string>());
  current = $state<string | null>(null);
  anchor: string | null = null;
  scrollRequest = $state<{ id: string; n: number } | null>(null);
  focusRequest = $state<{ id: string; field: string; n: number } | null>(null);
  dialog = $state<null | "new" | "palette" | "conflicts" | { pickParent: string; candidates: Suggestion[] }>(null);
  toast = $state<string | null>(null);
  perf = $state({ api: 0, render: 0 });
  problemCursor = -1;
  flushers = new Set<() => void>();
  private toastTimer: ReturnType<typeof setTimeout> | undefined;
  private seq = 0;

  // -- helpers -------------------------------------------------------
  type(it: Item) { return this.model.types[it.type]; }
  category(it: Item) { return this.type(it)?.states[it.state] ?? "Proposed"; }
  levelIndex(it: Item) { return LEVELS.indexOf(this.type(it)?.level ?? ""); }
  issuesFor(id: string) { return this.issuesBy.get(id) ?? []; }
  get item() { return this.current ? this.items.get(this.current) : undefined; }
  say(msg: string) {
    this.toast = msg;
    clearTimeout(this.toastTimer);
    this.toastTimer = setTimeout(() => (this.toast = null), 4000);
  }

  // -- backend -------------------------------------------------------
  async call(name: string, ...args: unknown[]): Promise<Resp> {
    const api = window.pywebview?.api;
    if (!api) throw new Error("Not running inside the Backlog Desk window (use `po gui`).");
    const t = performance.now();
    const r = await api[name](...args);
    this.perf.api = performance.now() - t;
    return r;
  }

  async mutate(name: string, ...args: unknown[]): Promise<Resp> {
    this.flush();
    const r = await this.call(name, ...args);
    this.apply(r);
    if (r.ok === false && r.error) this.say(r.error);
    if (r.skipped?.length) this.say(`${r.skipped.length} item(s) skipped: ${r.skipped[0].reason}`);
    if (r.note) this.say(r.note);
    return r;
  }

  flush() { for (const f of [...this.flushers]) f(); }

  async load() {
    try {
      const snap = await this.call("snapshot");
      this.settings = snap.settings ?? this.settings;
      if (!snap.path) {
        try {
          const th = localStorage.getItem("bd-theme"), de = localStorage.getItem("bd-density");
          this.settings = { ...this.settings, ...(th ? { theme: th as Settings["theme"] } : {}), ...(de ? { density: de as Settings["density"] } : {}) };
        } catch { /* ignore */ }
      }
      this.applyTheme();
      if (snap.error) { this.error = snap.error; this.loaded = true; return; }
      this.snapshot(snap);
      for (const id of this.kids.get(null) ?? []) this.expanded.add(id);
      if (this.items.size < 200) this.expanded = new Set(this.items.keys());
      else this.expanded = new Set(this.kids.get(null) ?? []);
      this.rebuild();
      this.loaded = true;
      const first = this.rows[0]?.id;
      if (first) this.select(first);
    } catch (e) {
      this.error = String((e as Error).message ?? e);
      this.loaded = true;
    }
  }

  snapshot(s: Resp) {
    this.model = s.model; this.people = s.people ?? {}; this.iterations = s.iterations ?? {}; this.path = s.path ?? null;
    this.items = new Map((s.items as Item[]).map((i) => [i.id, i]));
    this.indexKids();
    this.state(s);
  }

  state(r: Resp) {
    if (r.issues) {
      this.issues = r.issues;
      const by = new Map<string, Issue[]>();
      for (const i of r.issues as Issue[]) if (i.itemId) (by.get(i.itemId) ?? by.set(i.itemId, []).get(i.itemId)!).push(i);
      this.issuesBy = by;
    }
    if (r.status) this.status = r.status;
    if (r.conflicts) {
      this.conflicts = r.conflicts;
      if (r.conflicts.length && this.dialog === null) this.dialog = "conflicts";
      if (!r.conflicts.length && this.dialog === "conflicts") this.dialog = null;
    }
    if (r.canUndo !== undefined) this.canUndo = r.canUndo;
    if (r.canRedo !== undefined) this.canRedo = r.canRedo;
  }

  apply(r: Resp) {
    if (r.snapshot) {
      this.snapshot(r.snapshot);
      this.say("The file changed on disk and was merged with your edits.");
    } else {
      if (r.items) {
        const m = new Map(this.items);
        for (const it of r.items as Item[]) m.set(it.id, it);
        for (const id of (r.deleted ?? []) as string[]) m.delete(id);
        this.items = m;
      }
      this.state(r);
    }
    this.indexKids();
    if (r.selectId && this.items.has(r.selectId)) this.reveal(r.selectId);
    else this.rebuild();
    if (this.current && !this.items.has(this.current)) { this.current = null; this.selected = new Set(); }
  }

  async poll() {
    if (!window.pywebview?.api) return;
    try {
      const r = await window.pywebview.api.poll();
      if (r.changed) this.apply(r);
      else this.state(r);
    } catch { /* window closing */ }
  }

  // -- view model ----------------------------------------------------
  indexKids() {
    const kids = new Map<string | null, string[]>();
    for (const it of this.items.values()) {
      const p = it.parent ?? null;
      (kids.get(p) ?? kids.set(p, []).get(p)!).push(it.id);
    }
    for (const ids of kids.values()) ids.sort((a, b) => (this.items.get(a)!.rank - this.items.get(b)!.rank) || (a < b ? -1 : 1));
    this.kids = kids;
  }

  get filtering() {
    return !!(this.filter || this.fTypes.size || this.fStates.size || this.fIterations.size || this.mine);
  }

  rebuild() {
    const t0 = performance.now();
    const f = this.filter.trim().toLowerCase();
    const me = this.settings.currentUser;
    const hit = (it: Item) =>
      (!f || it.title.toLowerCase().includes(f) || it.id.toLowerCase().includes(f)) &&
      (!this.fTypes.size || this.fTypes.has(it.type)) &&
      (!this.fStates.size || this.fStates.has(it.state)) &&
      (!this.fIterations.size || this.fIterations.has(it.iteration ?? "")) &&
      (!this.mine || (!!me && it.assignedTo === me));
    const filtering = this.filtering;
    const matches = new Map<string, boolean>();
    const visit = (id: string): boolean => {
      const it = this.items.get(id)!;
      if (!this.showRemoved && this.category(it) === "Removed") return false;
      let any = !filtering || hit(it);
      for (const c of this.kids.get(id) ?? []) if (visit(c)) any = true;
      matches.set(id, any);
      return any;
    };
    for (const r of this.kids.get(null) ?? []) visit(r);
    const rows: Row[] = [];
    const walk = (id: string, depth: number) => {
      if (!matches.get(id)) return;
      rows.push({ id, depth });
      if (this.expanded.has(id) || filtering) for (const c of this.kids.get(id) ?? []) walk(c, depth + 1);
    };
    for (const r of this.kids.get(null) ?? []) walk(r, 0);
    this.rows = rows;
    requestAnimationFrame(() => (this.perf.render = performance.now() - t0));
  }

  toggle(id: string) {
    const s = new Set(this.expanded);
    s.has(id) ? s.delete(id) : s.add(id);
    this.expanded = s;
    this.rebuild();
  }
  expandAll() {
    const s = new Set<string>();
    for (const [id, k] of this.kids) if (id && k.length) s.add(id);
    this.expanded = s;
    this.rebuild();
  }
  collapseAll() { this.expanded = new Set(); this.rebuild(); }

  // -- selection -----------------------------------------------------
  select(id: string, scroll = true) {
    this.current = id; this.anchor = id; this.selected = new Set([id]);
    if (scroll) this.scrollRequest = { id, n: ++this.seq };
  }
  clickRow(id: string, e: MouseEvent) {
    if (e.shiftKey && this.anchor) {
      const a = this.rows.findIndex((r) => r.id === this.anchor), b = this.rows.findIndex((r) => r.id === id);
      if (a >= 0 && b >= 0) {
        this.selected = new Set(this.rows.slice(Math.min(a, b), Math.max(a, b) + 1).map((r) => r.id));
        this.current = id;
        return;
      }
    }
    if (e.ctrlKey || e.metaKey) {
      const s = new Set(this.selected);
      s.has(id) ? s.delete(id) : s.add(id);
      this.selected = s; this.current = id; this.anchor = id;
      return;
    }
    this.select(id, false);
  }
  /** Select an item, expanding its ancestors and making sure it is not filtered out. */
  reveal(id: string) {
    const s = new Set(this.expanded);
    let p = this.items.get(id)?.parent;
    while (p) { s.add(p); p = this.items.get(p)?.parent; }
    this.expanded = s;
    this.view = "tree";
    this.rebuild();
    if (!this.rows.some((r) => r.id === id)) {
      this.filter = ""; this.fTypes = new Set(); this.fStates = new Set(); this.fIterations = new Set(); this.mine = false;
      if (this.category(this.items.get(id)!) === "Removed") this.showRemoved = true;
      this.rebuild();
    }
    this.select(id);
  }
  focusField(id: string, field: string) {
    this.reveal(id);
    this.focusRequest = { id, field, n: ++this.seq };
  }
  nextProblem(dir = 1) {
    const withItem = this.issues.filter((i) => i.itemId && this.items.has(i.itemId));
    if (!withItem.length) return this.say("No problems.");
    this.problemCursor = (this.problemCursor + dir + withItem.length) % withItem.length;
    const p = withItem[this.problemCursor];
    this.focusField(p.itemId!, p.field ?? "title");
  }

  // -- edits ---------------------------------------------------------
  edit(id: string, field: string, value: unknown) { return this.mutate("set_field", id, field, value); }
  undo() { return this.mutate("undo"); }
  redo() { return this.mutate("redo"); }
  remove(id: string) { return this.mutate("remove", id); }
  async deleteItem(id: string) {
    const it = this.items.get(id);
    if (!it) return;
    if (it.remotes && Object.keys(it.remotes).length) return this.remove(id);
    if (!confirm(`Delete ${id} permanently? (Undo can bring it back.)`)) return;
    return this.mutate("delete", id);
  }

  /** Sibling ids of an item (including itself), in rank order. */
  siblings(id: string) { return this.kids.get(this.items.get(id)?.parent ?? null) ?? []; }
  moveBy(id: string, delta: number) {
    const sibs = this.siblings(id).filter((s) => s !== id);
    const cur = this.siblings(id).indexOf(id);
    const idx = Math.max(0, Math.min(sibs.length, cur + delta));
    if (idx === cur) return;
    return this.mutate("move", id, this.items.get(id)?.parent ?? null, idx);
  }
  /** Tab / Shift+Tab: move under the next / previous row one level above (the parent's neighbour). */
  reparentStep(id: string, dir: 1 | -1) {
    const it = this.items.get(id);
    const parent = it?.parent ? this.items.get(it.parent) : undefined;
    if (!it || !parent) return;
    const uncles = this.siblings(parent.id);
    const target = uncles[uncles.indexOf(parent.id) + dir];
    if (!target) return this.say("No neighbouring parent to move under.");
    return this.mutate("move", id, target, dir === 1 ? 0 : null);
  }

  suggest(kind: string, query: string, forType?: string, limit = 12): Promise<Suggestion[]> {
    return this.call("suggest", kind, query, limit, forType ?? null) as unknown as Promise<Suggestion[]>;
  }

  // -- settings ------------------------------------------------------
  applyTheme() {
    document.documentElement.dataset.theme = this.settings.theme;
    document.body.classList.toggle("comfortable", this.settings.density === "comfortable");
  }
  async setSetting(key: keyof Settings, value: unknown) {
    this.settings = { ...this.settings, [key]: value } as Settings;
    this.applyTheme();
    // no file means no .backlogdesk/ folder: remember theme and density in the browser instead
    try { localStorage.setItem("bd-" + key, String(value)); } catch { /* private mode */ }
    if (key === "density") this.rebuild();
    const r = await this.call("set_setting", key, value);
    if (r.ok === false) this.say(r.error);
    else this.settings = r.settings;
    if (key === "currentUser") { if (!value) this.mine = false; this.rebuild(); }
  }
}

export const app = new AppState();
