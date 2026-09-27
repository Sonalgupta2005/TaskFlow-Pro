import { useEffect, useState } from 'react';
import { fetchTasks, updateTask, type Task, type TaskStatus } from '../api/client';
import { TaskCard } from './TaskCard';
import { 
  DndContext, 
  closestCorners, 
  KeyboardSensor, 
  PointerSensor, 
  useSensor, 
  useSensors, 
  type DragEndEvent 
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import toast from 'react-hot-toast';
import { DroppableColumn } from './DroppableColumn';
import { TaskEditor } from './TaskEditor';

const COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: 'backlog', title: 'Backlog' },
  { id: 'in_progress', title: 'In Progress' },
  { id: 'review', title: 'Review' },
  { id: 'done', title: 'Done' }
];

export const KanbanBoard = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const loadTasks = async () => {
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;
    
    const taskId = active.id as string;
    const newStatus = over.id as TaskStatus;
    
    const task = tasks.find(t => t.id === taskId);
    if (!task || task.status === newStatus) return;

    if (task.status !== 'backlog' && newStatus === 'backlog') {
      toast.error(`Cannot move an active or completed task back to backlog.`);
      return;
    }

    const isMovingForward = (task.status === 'backlog' && newStatus !== 'backlog') || 
                            (task.status === 'in_progress' && (newStatus === 'review' || newStatus === 'done')) ||
                            (task.status === 'review' && newStatus === 'done');

    if (task.blocked && isMovingForward) {
      toast.error(`Task ${task.id} is blocked by prerequisites.`);
      return;
    }

    // Optimistic update
    const previousTasks = [...tasks];
    setTasks(tasks.map(t => t.id === taskId ? { ...t, status: newStatus } : t));

    try {
      await updateTask(taskId, { status: newStatus });
      await loadTasks();
    } catch (error: any) {
      setTasks(previousTasks);
      toast.error(error.response?.data?.detail || 'Failed to move task');
    }
  };

  const [editingTask, setEditingTask] = useState<Task | null>(null);

  if (loading) return <div style={{ padding: '2rem' }}>Loading board...</div>;

  const sortedTasks = [...tasks].sort((a, b) => {
    const pStartA = new Date(a.start_date).getTime() || 0;
    const pStartB = new Date(b.start_date).getTime() || 0;
    if (pStartA !== pStartB) return pStartA - pStartB;
    
    const endA = new Date(a.end_date).getTime() || 0;
    const endB = new Date(b.end_date).getTime() || 0;
    if (endA !== endB) return endA - endB;
    
    const createdA = new Date(a.created_at).getTime() || 0;
    const createdB = new Date(b.created_at).getTime() || 0;
    return createdA - createdB;
  });

  return (
    <div className="kanban-container">
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragEnd={handleDragEnd}>
        {COLUMNS.map(col => (
          <DroppableColumn key={col.id} id={col.id} title={col.title}>
            {sortedTasks.filter(t => t.status === col.id).map(task => (
              <div key={task.id} onDoubleClick={() => setEditingTask(task)}>
                <TaskCard task={task} />
              </div>
            ))}
          </DroppableColumn>
        ))}
      </DndContext>
      {editingTask && (
        <TaskEditor 
          taskToEdit={editingTask} 
          onClose={() => setEditingTask(null)} 
          onSuccess={loadTasks} 
        />
      )}
    </div>
  );
};
