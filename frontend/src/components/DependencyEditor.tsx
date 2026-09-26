import { useState, useEffect } from 'react';
import { type Task, type Dependency, type DependencySuggestion, fetchTasks, fetchDependencies, createDependency, removeDependency, fetchSuggestions, acceptSuggestion, dismissSuggestion } from '../api/client';
import { X, Sparkles, Check, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export const DependencyEditor = ({ onClose }: { onClose: () => void }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [deps, setDeps] = useState<Dependency[]>([]);
  const [suggestions, setSuggestions] = useState<DependencySuggestion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  
  const [prereq, setPrereq] = useState('');
  const [dependent, setDependent] = useState('');
  
  const load = async () => {
    setTasks(await fetchTasks());
    setDeps(await fetchDependencies());
  };

  useEffect(() => {
    load();
  }, []);

  const handleGenerateSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const data = await fetchSuggestions();
      setSuggestions(data);
      if (data.length === 0) toast('No new suggestions found');
      else toast.success(`Found ${data.length} suggestions`);
    } catch (err) {
      toast.error('Failed to get suggestions');
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleAccept = async (id: number) => {
    try {
      await acceptSuggestion(id);
      setSuggestions(prev => prev.filter(s => s.id !== id));
      await load();
      toast.success('Suggestion accepted');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to accept');
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      await dismissSuggestion(id);
      setSuggestions(prev => prev.filter(s => s.id !== id));
    } catch (err) {
      toast.error('Failed to dismiss');
    }
  };

  const handleAdd = async () => {
    if (!prereq || !dependent) {
      toast.error('Select both tasks');
      return;
    }
    try {
      await createDependency(prereq, dependent);
      setPrereq('');
      setDependent('');
      await load();
      toast.success('Dependency added');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to add dependency');
    }
  };

  const handleRemove = async (p: string, d: string) => {
    try {
      await removeDependency(p, d);
      await load();
      toast.success('Dependency removed');
    } catch (err) {
      toast.error('Failed to remove dependency');
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'var(--modal-backdrop)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}>
      <div className="glass-panel" style={{ width: '600px', borderRadius: 'var(--radius-xl)', padding: '2rem', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Manage Dependencies</h2>
          <button onClick={onClose} className="btn-ghost" style={{ padding: '0.25rem', border: 'none', cursor: 'pointer', background: 'transparent' }}><X /></button>
        </div>
        
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Prerequisite Task</label>
            <select className="input-field" value={prereq} onChange={e => setPrereq(e.target.value)}>
              <option value="">Select...</option>
              {tasks.map(t => <option key={t.id} value={t.id}>{t.id} - {t.title}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Dependent Task</label>
            <select className="input-field" value={dependent} onChange={e => setDependent(e.target.value)}>
              <option value="">Select...</option>
              {tasks.map(t => <option key={t.id} value={t.id}>{t.id} - {t.title}</option>)}
            </select>
          </div>
          <button className="btn" onClick={handleAdd}>Add Edge</button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', gap: '2rem' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>AI Suggestions</h3>
              <button className="btn" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={handleGenerateSuggestions} disabled={loadingSuggestions}>
                <Sparkles size={12} /> {loadingSuggestions ? 'Analyzing...' : 'Auto-Suggest'}
              </button>
            </div>
            
            {suggestions.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic', background: 'var(--empty-bg)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>Click Auto-Suggest to find dependencies based on task descriptions.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {suggestions.map(s => (
                  <div key={s.id} style={{ padding: '0.75rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(99, 102, 241, 0.2)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <div style={{ fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{s.suggested_prereq_id}</span>
                        <span style={{ margin: '0 0.5rem' }}>→</span>
                        <span style={{ fontWeight: 600 }}>{s.task_id}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button onClick={() => handleAccept(s.id)} style={{ color: 'var(--status-ready-text)', background: 'transparent', border: 'none', cursor: 'pointer' }} title="Accept"><Check size={16} /></button>
                        <button onClick={() => handleDismiss(s.id)} style={{ color: 'var(--text-muted)', background: 'transparent', border: 'none', cursor: 'pointer' }} title="Dismiss"><XCircle size={16} /></button>
                      </div>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{s.rationale}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Existing Dependencies</h3>
            {deps.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic' }}>No dependencies defined.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {deps.map(d => {
                  return (
                    <div key={`${d.prerequisite_id}-${d.dependent_id}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', background: 'var(--bg-main)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', alignItems: 'center' }}>
                      <div style={{ fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>{d.prerequisite_id}</span>
                        <span style={{ color: 'var(--text-muted)', margin: '0 0.5rem' }}>→</span>
                        <span style={{ fontWeight: 600 }}>{d.dependent_id}</span>
                      </div>
                      <button onClick={() => handleRemove(d.prerequisite_id, d.dependent_id)} style={{ color: 'var(--status-blocked-text)', background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.75rem' }}>Remove</button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
