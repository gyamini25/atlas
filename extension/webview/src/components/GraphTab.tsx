import { useMemo } from 'react';
import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow';
import 'reactflow/dist/style.css';

interface SubNode { id: string; kind: string; label: string; meta: Record<string, string> }
interface SubEdge { source: string; target: string; kind: string }
export interface Subgraph { root: string; nodes: SubNode[]; edges: SubEdge[] }

const KIND_COLOR: Record<string, string> = {
  code_symbol: '#7c6cff',
  commit: '#8b8b8b',
  pull_request: '#58a6ff',
  incident: '#f85149',
  adr: '#9d7bff',
  developer: '#3fb950',
  discussion: '#d29922',
  issue: '#3fb950',
  doc: '#8b8b8b',
};

export function GraphTab({ subgraph }: { subgraph: Subgraph | null }) {
  const { nodes, edges } = useMemo(() => toFlow(subgraph), [subgraph]);

  if (!subgraph || !subgraph.nodes.length) {
    return (
      <div className="empty">
        <div className="big">🕸️</div>
        The knowledge graph for this symbol will appear here after you Ask Atlas.
      </div>
    );
  }
  return (
    <div className="graph-wrap">
      <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}>
        <Background color="#333" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

function toFlow(sub: Subgraph | null): { nodes: Node[]; edges: Edge[] } {
  if (!sub) return { nodes: [], edges: [] };
  // Simple radial layout: root centre, others on a ring (stable, no layout dep).
  const others = sub.nodes.filter((n) => n.id !== sub.root);
  const nodes: Node[] = sub.nodes.map((n, i) => {
    const isRoot = n.id === sub.root;
    const idx = others.indexOf(n);
    const angle = (idx / Math.max(others.length, 1)) * Math.PI * 2;
    const radius = 220;
    return {
      id: n.id,
      data: { label: truncate(n.label) },
      position: isRoot
        ? { x: 0, y: 0 }
        : { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius },
      style: {
        background: 'var(--card)',
        color: 'var(--fg)',
        border: `1px solid ${KIND_COLOR[n.kind] ?? '#555'}`,
        borderRadius: 8,
        fontSize: 10,
        padding: 6,
        width: 150,
      },
    };
  });
  const edges: Edge[] = sub.edges.map((e, i) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.kind,
    animated: e.kind === 'modifies' || e.kind === 'resolves',
    style: { stroke: '#555' },
    labelStyle: { fill: 'var(--muted)', fontSize: 9 },
  }));
  return { nodes, edges };
}

function truncate(s: string): string {
  return s.length > 40 ? s.slice(0, 38) + '…' : s;
}
