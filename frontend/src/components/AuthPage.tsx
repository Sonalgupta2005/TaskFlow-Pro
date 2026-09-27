import React, { useState } from 'react';
import { login, register } from '../api/client';
import toast from 'react-hot-toast';
import { Eye, EyeOff } from 'lucide-react';

export const AuthPage = ({ onAuthSuccess }: { onAuthSuccess: (token: string) => void }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      toast.error('Please enter username and password');
      return;
    }
    
    setLoading(true);
    try {
      if (isLogin) {
        const { access_token } = await login(username, password);
        onAuthSuccess(access_token);
      } else {
        await register(username, password);
        toast.success('Registration successful');
        const { access_token } = await login(username, password);
        onAuthSuccess(access_token);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'var(--bg-main)' }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '400px', padding: '2rem', borderRadius: 'var(--radius-xl)' }}>
        <h1 className="logo" style={{ justifyContent: 'center', marginBottom: '2rem' }}>TaskFlow Pro</h1>
        
        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', fontWeight: 600 }}>{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
        
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Username</label>
            <input 
              type="text" 
              className="input-field" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              style={{ width: '100%' }}
              placeholder="Username"
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Password</label>
            <div style={{ position: 'relative' }}>
              <input 
                type={showPassword ? "text" : "password"} 
                className="input-field" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                style={{ width: '100%', paddingRight: '2.5rem' }}
                placeholder="Password"
              />
              <button 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer', display: 'flex', zIndex: 10 }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          <button type="submit" className="btn" disabled={loading} style={{ marginTop: '1rem', width: '100%' }}>
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>
        
        <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button type="button" onClick={() => setIsLogin(!isLogin)} className="btn-ghost" style={{ padding: '0.25rem', border: 'none', color: 'var(--accent-primary)' }}>
            {isLogin ? 'Register' : 'Login'}
          </button>
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.75rem', color: 'var(--text-muted)', opacity: 0.8 }}>
          Use a simple username and password for testing
        </div>
      </div>
    </div>
  );
};
