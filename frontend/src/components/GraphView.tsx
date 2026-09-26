import { useState, useEffect } from 'react';
import ReactFlow, { Background, Controls, type Node, type Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import {fetchTasks, fetchDependencies } from '../api/client';
import { X } from 'lucide-react';

export const GraphView = ({ onClose }: { onClose: () => void }) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  useEffect(() => {
    const load = async () => {
      const tasks = await fetchTasks();
      const deps = await fetchDependencies();

      // Simple layout: position tasks based on column and index
      const colMap = { backlog: 0, in_progress: 1, review: 2, done: 3 };
      
      const newNodes: Node[] = tasks.map(t => ({
        id: t.id,
        position: { x: colMap[t.status] * 300 + 50, y: t.position * 100 + 50 },
        data: { label: `${t.id}: ${t.title}` },
        style: {
          background: t.is_critical ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          border: `1px solid ${t.is_critical ? '#EF4444' : 'var(--border-color)'}`,
          borderRadius: 'var(--radius-md)',
          padding: '10px',
          width: 200,
        },
      }));

      const newEdges: Edge[] = deps.map(d => ({
        id: `${d.prerequisite_id}-${d.dependent_id}`,
        source: d.prerequisite_id,
        target: d.dependent_id,
        animated: true,
        style: { stroke: 'var(--accent-primary)' }
      }));

      setNodes(newNodes);
      setEdges(newEdges);
    };
    load();
  }, []);

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--bg-main)', zIndex: 2000, display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '1rem 2rem', display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', background: 'var(--bg-glass)' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Dependency Graph</h2>
        <button onClick={onClose} className="btn-ghost" style={{ padding: '0.25rem', border: 'none', cursor: 'pointer' }}><X /></button>
      </div>
      <div style={{ flex: 1 }}>
        <ReactFlow nodes={nodes} edges={edges} fitView>
          <Background color="var(--border-color)" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};
