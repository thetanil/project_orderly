export interface TypeInfo {
  level: string;
  label: string;
  color: string;
  estimation: "forbidden" | "optional" | "required";
  priority: "optional" | "required";
  states: Record<string, string>;
}
export interface Model { types: Record<string, TypeInfo> }
export interface Rollup { storyPoints: number; estimatedCount: number; unestimatedCount: number; notEstimableCount: number }
export interface Item {
  id: string; type: string; title: string; state: string; parent?: string | null; rank: number;
  iteration?: string; assignedTo?: string; priority?: number; storyPoints?: number;
  description?: string; acceptanceCriteria?: string; localNotes?: string; tags?: string[];
  rollup?: Rollup; remotes?: Record<string, unknown>;
  [k: string]: unknown;
}
export interface Person { id: string; name: string }
export interface Iteration { id: string; name: string; path: string }
export interface Issue { rule: string; level: "E" | "W"; itemId: string | null; field: string | null; message: string; fix?: string }
export interface Status { state: string; errors: number; warnings: number; conflicts: number; message: string | null }
export interface Conflict { itemId: string; field: string | null; mine: unknown; theirs: unknown }
export interface Settings { currentUser: string | null; theme: "dark" | "light"; density: "compact" | "comfortable" }
export interface Row { id: string; depth: number }
export interface Suggestion { id?: string; title?: string; name?: string; label?: string; type?: string; tag?: string; count?: number; path?: string }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Resp = Record<string, any>;

declare global {
  interface Window { pywebview?: { api: Record<string, (...a: unknown[]) => Promise<any>> } }
}
