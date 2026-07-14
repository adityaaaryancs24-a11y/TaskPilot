import { useEffect, useMemo } from "react";
import ReactFlow, { Node, Edge, Background, Controls, useNodesState, useEdgesState } from "reactflow";
import "reactflow/dist/style.css";

const SOURCE_BG: Record<string, string> = {
  jira: "#F7C5E6",
  defect: "#F7C5E6",
  email: "#C9D8FF",
  github: "#DCC7F7",
  slack: "#F5D66E",
  transcript: "#BFD78D",
};

const SOURCE_LABELS: Record<string, string> = {
  jira: "Jira",
  defect: "Defect",
  email: "Email",
  github: "GitHub",
  slack: "Slack",
  transcript: "Transcript",
};

export function DependencyGraph({ tasks }: { tasks: any[] }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!tasks?.length) return;

    const taskMap = Object.fromEntries(tasks.map((t) => [t.id, t]));
    const newNodes: Node[] = [];
    const edgeSet = new Set<string>();
    const newEdges: Edge[] = [];

    tasks.forEach((task, i) => {
      const label = task.title?.length > 25 ? task.title.slice(0, 22) + "..." : task.title || task.id;
      newNodes.push({
        id: task.id,
        data: { label },
        position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 110 },
        style: {
          background: SOURCE_BG[task.source_type] || "#F6F2E9",
          color: "#111111",
          padding: "8px 14px",
          borderRadius: 12,
          border: "1px solid #E9E4D8",
          fontSize: 11,
          fontFamily: "'IBM Plex Mono', monospace",
          maxWidth: 180,
        },
      });

      (task.dependencies || []).forEach((depId: string) => {
        if (taskMap[depId]) {
          const key = `${depId}->${task.id}`;
          if (!edgeSet.has(key)) {
            edgeSet.add(key);
            newEdges.push({
              id: key,
              source: depId,
              target: task.id,
              type: "smoothstep",
              animated: true,
              style: { stroke: "#F7C5E6", strokeWidth: 2 },
            });
          }
        }
      });

      (task.blocks || []).forEach((blockedId: string) => {
        if (taskMap[blockedId]) {
          const key = `${task.id}->${blockedId}`;
          if (!edgeSet.has(key)) {
            edgeSet.add(key);
            newEdges.push({
              id: key,
              source: task.id,
              target: blockedId,
              type: "smoothstep",
              animated: true,
              style: { stroke: "#BFD78D", strokeWidth: 2 },
            });
          }
        }
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [tasks, setNodes, setEdges]);

  const hasDeps = edges.length > 0;

  return (
    <div>
      {hasDeps ? (
        <div style={{ width: "100%", height: 380, borderRadius: 14, overflow: "hidden", border: "1px solid #E9E4D8" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            attributionPosition="bottom-left"
            minZoom={0.3}
            maxZoom={2}
            style={{ background: "#F6F2E9" }}
          >
            <Background color="#E9E4D8" gap={16} />
            <Controls style={{ background: "#FFFFFF", border: "1px solid #E9E4D8", borderRadius: 12 }} />
          </ReactFlow>
        </div>
      ) : (
        <div style={{ padding: "24px 18px", textAlign: "center", color: "#7A7A7A", fontSize: 12, border: "1px solid #E9E4D8", borderRadius: 14 }}>
          No dependency relationships found. Tasks with <code style={{ background: "#F6F2E9", padding: "2px 6px", borderRadius: 4, fontSize: 11 }}>dependencies</code> or <code style={{ background: "#F6F2E9", padding: "2px 6px", borderRadius: 4, fontSize: 11 }}>blocks</code> fields will appear here.
        </div>
      )}
    </div>
  );
}
