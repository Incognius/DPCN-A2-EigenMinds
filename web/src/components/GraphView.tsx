import { useEffect, useRef, useState } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { Maximize2, Minus, Plus } from "lucide-react";

export interface GNode { id: string; x: number; y: number; size: number; color: string; label: string; muted?: boolean }
export interface GEdge { s: string; t: string; color?: string; size?: number }

/**
 * WebGL network view. Positions are precomputed in Python, so the first frame is final.
 * Hover highlights a node's neighbourhood; `dim` greys nodes outside a filter.
 */
export default function GraphView({ nodes, edges, height = 560, directed = false, onNode, focus, edgeColor = "rgba(210,170,200,0.10)", labelThreshold = 9 }: {
  nodes: GNode[]; edges: GEdge[]; height?: number; directed?: boolean;
  onNode?: (id: string) => void; focus?: string | null; edgeColor?: string; labelThreshold?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const hoverRef = useRef<string | null>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const g = new Graph({ type: directed ? "directed" : "undirected", multi: false, allowSelfLoops: false });
    for (const n of nodes) g.addNode(n.id, { x: n.x, y: n.y, size: n.size, color: n.color, label: n.label, muted: n.muted });
    for (const e of edges) {
      if (e.s !== e.t && g.hasNode(e.s) && g.hasNode(e.t) && !g.hasEdge(e.s, e.t)) g.addEdge(e.s, e.t, { color: e.color ?? edgeColor, size: e.size ?? 0.6 });
    }
    graphRef.current = g;
    const renderer = new Sigma(g, ref.current, {
      renderLabels: true,
      labelRenderedSizeThreshold: labelThreshold,
      labelColor: { color: "#e9dfe7" },
      labelFont: "Urbanist, system-ui, sans-serif",
      labelSize: 12,
      labelWeight: "600",
      defaultEdgeType: directed ? "arrow" : "line",
      zIndex: true,
      minCameraRatio: 0.08,
      maxCameraRatio: 3,
      nodeReducer: (node, data) => {
        const h = hoverRef.current;
        const res = { ...data } as Record<string, unknown>;
        if (data.muted) { res.color = "#3a3238"; res.label = ""; res.zIndex = 0; }
        if (h) {
          if (node === h || g.areNeighbors(node, h)) { res.zIndex = 2; res.highlighted = node === h; res.label = data.label; res.color = data.color; }
          else { res.color = "#2a2328"; res.label = ""; res.zIndex = 0; }
        }
        return res;
      },
      edgeReducer: (edge, data) => {
        const h = hoverRef.current;
        if (!h) return data;
        const [s, t] = g.extremities(edge);
        return s === h || t === h ? { ...data, color: "rgba(240,210,232,0.55)", size: 1.2, zIndex: 1 } : { ...data, hidden: true };
      },
    });
    renderer.on("enterNode", ({ node }) => { hoverRef.current = node; setHover(node); renderer.refresh({ skipIndexation: true }); });
    renderer.on("leaveNode", () => { hoverRef.current = null; setHover(null); renderer.refresh({ skipIndexation: true }); });
    renderer.on("clickNode", ({ node }) => onNode?.(node));
    sigmaRef.current = renderer;
    return () => { renderer.kill(); sigmaRef.current = null; };
    // rebuild only when the data itself changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, directed]);

  useEffect(() => {
    const r = sigmaRef.current, g = graphRef.current;
    if (!r || !g || !focus || !g.hasNode(focus)) return;
    const pos = r.getNodeDisplayData(focus);
    if (pos) r.getCamera().animate({ x: pos.x, y: pos.y, ratio: 0.25 }, { duration: 600 });
    hoverRef.current = focus; setHover(focus); r.refresh({ skipIndexation: true });
  }, [focus]);

  const cam = (f: "in" | "out" | "reset") => {
    const c = sigmaRef.current?.getCamera();
    if (!c) return;
    if (f === "in") c.animatedZoom({ duration: 300 });
    else if (f === "out") c.animatedUnzoom({ duration: 300 });
    else c.animatedReset({ duration: 300 });
  };

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/[0.05]"
      style={{ height, background: "radial-gradient(700px 400px at 50% 40%, rgba(125,69,112,.16), transparent 70%), #0c090b" }}>
      <div ref={ref} className="absolute inset-0" />
      <div className="absolute right-3 top-3 flex flex-col gap-1.5">
        {([["in", Plus], ["out", Minus], ["reset", Maximize2]] as const).map(([k, Icon]) => (
          <button key={k} onClick={() => cam(k)} aria-label={`zoom ${k}`}
            className="grid h-8 w-8 place-items-center rounded-full border border-white/10 bg-[#120d11]/90 text-ink-2 hover:text-white">
            <Icon size={14} />
          </button>
        ))}
      </div>
      {hover && <div className="pointer-events-none absolute bottom-3 left-3 max-w-[70%] truncate rounded-full border border-white/10 bg-[#120d11]/90 px-3 py-1.5 text-[12px] text-ink-2">
        {nodes.find((n) => n.id === hover)?.label} · click for details
      </div>}
    </div>
  );
}
