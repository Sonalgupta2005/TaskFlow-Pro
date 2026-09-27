import { useState  } from 'react';
import { createTask, updateTask, deleteTask, createDependency, fetchDraftSuggestions, type Task, type DependencySuggestion } from '../api/client';
import { X, Lock, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';

export const TaskEditor = ({ onClose, onSuccess, taskToEdit }: { onClose: () => void, onSuccess: () => void, taskToEdit?: Task }) => {
  const [title, setTitle] = useState(taskToEdit?.title || '');
  const [description, setDescription] = useState(taskToEdit?.description || '');
  const [plannedStart, setPlannedStart] = useState(taskToEdit ? taskToEdit.planned_start : format(new Date(), 'yyyy-MM-dd'));
  const [duration, setDuration] = useState(taskToEdit?.duration_days || 1);
  const [loading, setLoading] = useState(false);

  const [suggestions, setSuggestions] = useState<DependencySuggestion[]>([]);
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  const [suggesting, setSuggesting] = useState(false);

  const isEdit = !!taskToEdit;
  const isDone = taskToEdit?.status === 'done';
  const isBacklog = taskToEdit?.status === 'backlog' || !isEdit;
  
  const canEditTitleDesc = !isDone;
  const canEditPlannedStart = isBacklog;
  const canEditDuration = !isDone;

  const handleSuggest = async () => {
    if (!title) {
      toast.error("Enter a title first to get suggestions");
      return;
    }
    setSuggesting(true);
    try {
      const draftId = taskToEdit?.id || `TASK-DRAFT`;
      const data = await fetchDraftSuggestions(title, description, draftId);
      setSuggestions(data);
      if (data.length === 0) {
        toast('No strong dependencies found.', { icon: 'ℹ️' });
      }
    } catch (err: any) {
      toast.error('Failed to get suggestions');
    } finally {
      setSuggesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) {
      toast.error('Title is required');
      return;
    }
    setLoading(true);
    try {
      let finalId = taskToEdit?.id;
      if (isEdit && finalId) {
        await updateTask(finalId, {
          title: canEditTitleDesc ? title : undefined,
          description: canEditTitleDesc ? description : undefined,
          planned_start: canEditPlannedStart ? plannedStart : undefined,
          duration_days: canEditDuration ? duration : undefined,
        });
        toast.success('Task updated');
      } else {
        const newTask = await createTask({
          title,
          description,
          planned_start: plannedStart,
          duration_days: duration,
        });
        finalId = newTask.id;
        toast.success(`Task ${finalId} created successfully`);
      }

      // Handle suggestions
      for (const s of suggestions) {
        if (selectedSuggestions.has(s.id) && finalId) {
          const p = s.prerequisite_id.startsWith('TASK-DRAFT') ? finalId : s.prerequisite_id;
          const d = s.dependent_id.startsWith('TASK-DRAFT') ? finalId : s.dependent_id;
          await createDependency(p, d);
        }
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to save task');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!taskToEdit) return;
    if (confirm('Are you sure you want to delete this task? All of its dependencies will also be removed.')) {
      setLoading(true);
      try {
        await deleteTask(taskToEdit.id);
        toast.success('Task deleted');
        onSuccess();
        onClose();
      } catch (err: any) {
        toast.error('Failed to delete task');
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--modal-backdrop)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}>
      <div className="glass-panel" style={{ width: '500px', maxHeight: '90vh', overflowY: 'auto', borderRadius: 'var(--radius-xl)', padding: '2rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>{isEdit ? 'Edit Task' : 'Create New Task'}</h2>
          <button onClick={onClose} className="btn-ghost" style={{ padding: '0.25rem', border: 'none', cursor: 'pointer', background: 'transparent' }}><X /></button>
        </div>
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Title {!canEditTitleDesc && <Lock size={12} />}
            </label>
            <input 
              type="text" 
              className="input-field" 
              value={title} 
              onChange={e => setTitle(e.target.value)} 
              placeholder="E.g., Design Database Schema"
              style={{ width: '100%', opacity: canEditTitleDesc ? 1 : 0.6 }}
              disabled={!canEditTitleDesc}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Description {!canEditTitleDesc && <Lock size={12} />}
            </label>
            <textarea 
              className="input-field" 
              value={description} 
              onChange={e => setDescription(e.target.value)} 
              placeholder="Task details..."
              style={{ width: '100%', minHeight: '80px', resize: 'vertical', opacity: canEditTitleDesc ? 1 : 0.6 }}
              disabled={!canEditTitleDesc}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Planned Start {!canEditPlannedStart && <Lock size={12} />}
              </label>
              <input 
                type="date" 
                className="input-field" 
                value={plannedStart} 
                onChange={e => setPlannedStart(e.target.value)} 
                min={!isEdit ? new Date().toISOString().split('T')[0] : undefined}
                style={{ width: '100%', opacity: canEditPlannedStart ? 1 : 0.6, colorScheme: 'light' }}
                disabled={!canEditPlannedStart}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                Duration (Days) {!canEditDuration && <Lock size={12} />}
              </label>
              <input 
                type="number" 
                min="1"
                className="input-field" 
                value={duration} 
                onChange={e => setDuration(parseInt(e.target.value) || 1)} 
                style={{ width: '100%', opacity: canEditDuration ? 1 : 0.6 }}
                disabled={!canEditDuration}
              />
            </div>
          </div>

          <div style={{ background: 'var(--bg-glass)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={16} style={{ color: 'var(--accent-primary)' }} /> AI Dependencies
              </span>
              <button type="button" onClick={handleSuggest} disabled={suggesting} className="btn-ghost" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', borderRadius: '4px', cursor: 'pointer', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                {suggesting ? 'Thinking...' : 'Auto Suggest'}
              </button>
            </div>
            
            {suggestions.length > 0 && (
              <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto', paddingRight: '0.5rem' }}>
                {suggestions.map(s => {
                  const isPrereq = s.dependent_id.startsWith('TASK-DRAFT') || s.dependent_id === taskToEdit?.id;
                  const label = isPrereq 
                    ? `Prerequisite: ${s.prerequisite_id}`
                    : `Dependent: ${s.dependent_id}`;
                    
                  return (
                    <label key={s.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', fontSize: '0.8rem', padding: '0.5rem', background: 'var(--bg-main)', borderRadius: '4px', border: '1px solid var(--border-color)', cursor: 'pointer' }}>
                      <input 
                        type="checkbox" 
                        checked={selectedSuggestions.has(s.id)}
                        onChange={(e) => {
                          const next = new Set(selectedSuggestions);
                          if (e.target.checked) next.add(s.id);
                          else next.delete(s.id);
                          setSelectedSuggestions(next);
                        }}
                        style={{ marginTop: '0.2rem' }}
                      />
                      <div>
                        <strong>{label}</strong>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.2rem' }}>{s.rationale}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
            {isEdit && (
              <button type="button" onClick={handleDelete} disabled={loading} className="btn-ghost" style={{ color: '#EF4444', marginRight: 'auto' }}>Delete</button>
            )}
            <button type="button" onClick={onClose} disabled={loading} className="btn-ghost">Cancel</button>
            <button type="submit" className="btn" disabled={loading}>
              {loading ? 'Saving...' : 'Save Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
