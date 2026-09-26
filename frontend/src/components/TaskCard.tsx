import type { Task } from '../api/client';
import { useDraggable } from '@dnd-kit/core';
import { Calendar, Clock } from 'lucide-react';
import { format } from 'date-fns';

export const TaskCard = ({ task }: { task: Task }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: task.id });
  
  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    zIndex: 100,
  } : undefined;

  let cardStyle: React.CSSProperties = {};
  if (task.status === 'done' && task.blocked) {
    cardStyle = { borderColor: 'rgba(234, 179, 8, 0.6)', boxShadow: '0 0 10px rgba(234, 179, 8, 0.15)' };
  } else if (task.is_critical) {
    cardStyle = { borderColor: 'rgba(239, 68, 68, 0.5)', boxShadow: '0 0 10px rgba(239, 68, 68, 0.1)' };
  }

  return (
    <div className="task-card" ref={setNodeRef} style={{...style, ...cardStyle}} {...listeners} {...attributes}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>{task.id}</span>
          {task.is_critical && <span style={{ fontSize: '0.65rem', color: '#EF4444', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>Critical</span>}
        </div>
        {task.status !== 'done' && (
          task.blocked ? 
            <span className="badge badge-blocked">Blocked</span> : 
            <span className="badge badge-ready">Ready</span>
        )}
      </div>
      
      {task.status === 'done' && task.blocked && (
        <div style={{ fontSize: '0.7rem', color: '#EAB308', background: 'rgba(234, 179, 8, 0.1)', padding: '0.4rem', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(234, 179, 8, 0.3)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          ⚠️ Prerequisites reopened - review required
        </div>
      )}

      <div className="task-title">{task.title}</div>
      <div className="task-desc">{task.description}</div>
      
      <div className="task-meta">
        <div className="task-dates">
          <Calendar size={12} />
          {format(new Date(task.start_date), 'MMM d')} - {format(new Date(task.end_date), 'MMM d')}
        </div>
        <div className="task-dates">
          <Clock size={12} />
          {task.duration_days}d
        </div>
      </div>
    </div>
  );
};
