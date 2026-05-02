import { MOCK_PRINTERS } from "../data/mock/printers";
import { MOCK_PLAN_DAG } from "../data/mock/dag";
import type { TaskDAG, TaskEdge, TaskNode } from "../types/dag";
import type { Printer, PrinterAdapter, PrinterDataSource, PrinterStatus } from "../types/printer";

type HermesImportMeta = ImportMeta & {
  env: {
    VITE_HERMES3D_BRIDGE_PORT?: string;
  };
};

const DEFAULT_BRIDGE_PORT = "8765";
const LIVE_BRIDGE_PORT =
  (import.meta as HermesImportMeta).env.VITE_HERMES3D_BRIDGE_PORT ?? DEFAULT_BRIDGE_PORT;
const LIVE_PRINTERS_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/printers`;
const LIVE_PLAN_PREVIEW_URL = `http://127.0.0.1:${LIVE_BRIDGE_PORT}/api/plan/preview`;

const MODELS = new Set<Printer["model"]>(["FLSUN T1", "FLSUN S1", "FLSUN V400", "Generic"]);
const STATUSES = new Set<PrinterStatus>([
  "online",
  "printing",
  "paused",
  "maintenance",
  "offline",
  "error",
]);
const ADAPTERS = new Set<PrinterAdapter>(["moonraker", "octoprint", "printrun", "manual"]);
const DATA_SOURCES = new Set<PrinterDataSource>(["mock", "live", "error"]);

export async function getLivePrinters(): Promise<Printer[]> {
  try {
    const response = await fetch(LIVE_PRINTERS_URL, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!response.ok) {
      return fallbackPrinters("error");
    }
    const payload: unknown = await response.json();
    const printers = parsePrinterArray(payload);
    return printers ?? fallbackPrinters("error");
  } catch {
    return fallbackPrinters("error");
  }
}

export async function planPreviewLive(prompt: string): Promise<TaskDAG> {
  try {
    const response = await fetch(LIVE_PLAN_PREVIEW_URL, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt }),
      cache: "no-store",
    });
    if (!response.ok) {
      return fallbackDag(prompt);
    }
    const payload: unknown = await response.json();
    return parseTaskDAG(payload) ?? fallbackDag(prompt);
  } catch {
    return fallbackDag(prompt);
  }
}

function parsePrinterArray(payload: unknown): Printer[] | null {
  if (!Array.isArray(payload)) {
    return null;
  }
  const printers = payload.map(parsePrinter);
  if (printers.some((printer) => printer == null)) {
    return null;
  }
  return printers as Printer[];
}

function parsePrinter(value: unknown): Printer | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.id) ||
    !isString(value.name) ||
    !isModel(value.model) ||
    !isNullableString(value.ip) ||
    !isStatus(value.status) ||
    !isAdapter(value.adapter) ||
    !isDataSource(value.data_source) ||
    !isNullableNumber(value.temp_hot) ||
    !isNullableNumber(value.temp_bed) ||
    !isNullableNumber(value.progress) ||
    !isNullableString(value.current_job) ||
    typeof value.maintenance_flag !== "boolean" ||
    !isNullableString(value.camera_url)
  ) {
    return null;
  }
  return {
    id: value.id,
    name: value.name,
    model: value.model,
    ip: value.ip,
    status: value.status,
    adapter: value.adapter,
    data_source: value.data_source,
    temp_hot: value.temp_hot,
    temp_bed: value.temp_bed,
    progress: value.progress,
    current_job: value.current_job,
    maintenance_flag: value.maintenance_flag,
    camera_url: value.camera_url,
  };
}

function parseTaskDAG(value: unknown): TaskDAG | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.dag_id) ||
    !isString(value.run_id) ||
    !Array.isArray(value.nodes) ||
    !Array.isArray(value.edges) ||
    !isNumber(value.max_depth) ||
    !isNumber(value.max_fanout) ||
    !isRecord(value.metadata)
  ) {
    return null;
  }
  const nodes = value.nodes.map(parseTaskNode);
  const edges = value.edges.map(parseTaskEdge);
  if (nodes.some((node) => node == null) || edges.some((edge) => edge == null)) {
    return null;
  }
  return {
    dag_id: value.dag_id,
    run_id: value.run_id,
    nodes: nodes as TaskNode[],
    edges: edges as TaskEdge[],
    max_depth: value.max_depth,
    max_fanout: value.max_fanout,
    metadata: value.metadata,
  };
}

function parseTaskNode(value: unknown): TaskNode | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.node_id) ||
    !isString(value.tool) ||
    !isString(value.kind) ||
    !isRecord(value.inputs) ||
    !isNumber(value.retry_budget) ||
    !isStringArray(value.gate_set) ||
    !isStringArray(value.depends_on)
  ) {
    return null;
  }
  return {
    node_id: value.node_id,
    tool: value.tool,
    kind: value.kind,
    inputs: value.inputs,
    retry_budget: value.retry_budget,
    gate_set: value.gate_set,
    depends_on: value.depends_on,
  };
}

function parseTaskEdge(value: unknown): TaskEdge | null {
  if (!isRecord(value)) {
    return null;
  }
  if (
    !isString(value.from_node) ||
    !isString(value.to_node) ||
    !isString(value.condition)
  ) {
    return null;
  }
  return {
    from_node: value.from_node,
    to_node: value.to_node,
    condition: value.condition,
  };
}

function fallbackPrinters(dataSource: PrinterDataSource): Printer[] {
  return MOCK_PRINTERS.map((printer) => ({ ...printer, data_source: dataSource }));
}

function fallbackDag(prompt: string): TaskDAG {
  return {
    ...MOCK_PLAN_DAG,
    metadata: {
      ...MOCK_PLAN_DAG.metadata,
      fallback_prompt: prompt,
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableNumber(value: unknown): value is number | null {
  return value === null || (typeof value === "number" && Number.isFinite(value));
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isModel(value: unknown): value is Printer["model"] {
  return typeof value === "string" && MODELS.has(value as Printer["model"]);
}

function isStatus(value: unknown): value is PrinterStatus {
  return typeof value === "string" && STATUSES.has(value as PrinterStatus);
}

function isAdapter(value: unknown): value is PrinterAdapter {
  return typeof value === "string" && ADAPTERS.has(value as PrinterAdapter);
}

function isDataSource(value: unknown): value is PrinterDataSource {
  return typeof value === "string" && DATA_SOURCES.has(value as PrinterDataSource);
}
