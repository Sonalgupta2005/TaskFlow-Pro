import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { Layers, Moon, Sun } from 'lucide-react';
import { KanbanBoard } from './components/KanbanBoard';
import { DependencyEditor } from './components/DependencyEditor';
import { GraphView } from './components/GraphView';

function App() {
  const [showDeps, setShowDeps] = useState(false);
  const [showGraph, setShowGraph] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <>
      <Toaster position="top-right" toastOptions={{ style: { background: '#131A2A', color: '#E2E8F0', border: '1px solid rgba(255,255,255,0.08)' } }} />
      <header className="header-bar">
        <div className="logo">
          <Layers size={24} style={{ color: 'var(--accent-primary)' }} />
          TaskFlow Pro
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button 
            className="btn-ghost" 
            style={{ padding: '0.4rem', border: 'none', cursor: 'pointer', display: 'flex' }}
            onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <button className="btn btn-ghost" onClick={() => setShowGraph(true)}>Graph View</button>
          <button className="btn btn-ghost" onClick={() => setShowDeps(true)}>Dependencies</button>
          <button className="btn">+ New Task</button>
        </div>
      </header>
      <main>
        <KanbanBoard key={refreshKey} />
      </main>
      
      {showDeps && (
        <DependencyEditor onClose={() => {
          setShowDeps(false);
          setRefreshKey(prev => prev + 1); // refresh board when dependencies change
        }} />
      )}
      
      {showGraph && (
        <GraphView onClose={() => setShowGraph(false)} />
      )}
    </>
  );
}

export default App;
