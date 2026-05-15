import React, { useState } from 'react';
import { Mail, ShieldCheck, ArrowRight, Lock } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const raw = await response.text();
      let data: any = {};
      if (raw) {
        try {
          data = JSON.parse(raw);
        } catch {
          data = { detail: raw };
        }
      }
      if (response.ok && data.status === 'success') {
        alert(data.message);
        navigate('/verify-otp', { state: { email } });
      } else {
        throw new Error(data.detail || data.message || `Access authorization failed (${response.status})`);
      }
    } catch (err) {
      alert(`[AUTH_NODE_ERROR] ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Authorize Access" subtitle="Connect to INGRES Dashboard">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Email Input */}
        <div className="space-y-2 group">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1 transition-colors group-focus-within:text-primary">
            Official E-Mail Vector
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-primary" />
            <input 
              required
              type="email" 
              placeholder="name@department.gov.in"
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-primary/50 transition-all font-bold"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </div>

        <button 
          disabled={isLoading}
          type="submit"
          className="w-full group relative overflow-hidden bg-primary p-4 rounded-2xl text-sm font-black uppercase tracking-widest text-white shadow-xl shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
        >
          <div className="relative z-10 flex items-center justify-center gap-2">
            {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
                <>
                    CONNECT HUB
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </>
            )}
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
        </button>

        <div className="grid grid-cols-2 gap-6 pt-4">
             <Link to="/register" className="flex flex-col items-center gap-2 p-4 bg-white/5 rounded-2xl border border-white/5 hover:bg-primary/10 transition-colors group text-center">
                <Lock className="w-4 h-4 text-text-muted transition-colors group-hover:text-primary" />
                <span className="text-[10px] font-black uppercase tracking-widest text-text-muted transition-colors group-hover:text-white">New Resident</span>
             </Link>
             <Link to="/portal/login" className="flex flex-col items-center gap-2 p-4 bg-white/5 rounded-2xl border border-white/5 hover:bg-accent-violet/10 transition-colors group text-center">
                <ShieldCheck className="w-4 h-4 text-text-muted transition-colors group-hover:text-accent-violet" />
                <span className="text-[10px] font-black uppercase tracking-widest text-text-muted transition-colors group-hover:text-white">Gov Portal Login</span>
             </Link>
        </div>
      </form>
    </AuthLayout>
  );
};

export default Login;
