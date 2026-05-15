import React, { useState } from 'react';
import { Mail, User, ShieldCheck, ArrowRight, Phone } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    role: 'user'
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
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
        localStorage.setItem('ingres_name', formData.name);
        localStorage.setItem('ingres_role', formData.role);
        navigate('/verify-otp', { state: { email: formData.email } });
      } else {
        throw new Error(data.detail || data.message || `Registration failed (${response.status})`);
      }
    } catch (err) {
      alert(`[SYSTEM_ERROR] ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Join JalSathi" subtitle="Initialize Your Neural Access">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name Input */}
        <div className="space-y-2 group">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1 transition-colors group-focus-within:text-primary">
            Citizen Identity
          </label>
          <div className="relative">
            <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-primary" />
            <input 
              required
              type="text" 
              placeholder="e.g. Akira Aravind"
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-primary/50 transition-all font-bold placeholder:text-white/10"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
          </div>
        </div>

        {/* Email Input */}
        <div className="space-y-2 group">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1 transition-colors group-focus-within:text-primary">
            Official E-Mail
          </label>
          <div className="relative">
            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-primary" />
            <input 
              required
              type="email" 
              placeholder="name@department.gov.in"
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-primary/50 transition-all font-bold placeholder:text-white/10"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>
        </div>

        {/* Phone Input */}
        <div className="space-y-2 group">
          <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1 transition-colors group-focus-within:text-primary">
            Contact Vector
          </label>
          <div className="relative">
            <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-primary" />
            <input 
              required
              type="tel" 
              placeholder="+91 00000 00000"
              className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-primary/50 transition-all font-bold placeholder:text-white/10"
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
            />
          </div>
        </div>

        {/* Role Selection */}
        <div className="grid grid-cols-2 gap-4">
          <div 
            onClick={() => setFormData({...formData, role: 'user'})}
            className={`cursor-pointer p-4 rounded-2xl border transition-all text-center ${formData.role === 'user' ? 'bg-primary/20 border-primary shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'bg-white/5 border-white/5 hover:border-white/10 opacity-60'}`}
          >
             <p className="text-[10px] font-black uppercase tracking-widest text-white">General</p>
          </div>
          <div 
            onClick={() => setFormData({...formData, role: 'official'})}
            className={`cursor-pointer p-4 rounded-2xl border transition-all text-center ${formData.role === 'official' ? 'bg-accent-violet/20 border-accent-violet shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 'bg-white/5 border-white/5 hover:border-white/10 opacity-60'}`}
          >
             <p className="text-[10px] font-black uppercase tracking-widest text-white">Official</p>
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
                    ENCRYPT & REGISTER
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </>
            )}
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
        </button>

        <div className="flex items-center justify-center gap-2 text-xs font-bold text-text-muted">
           <ShieldCheck className="w-3.5 h-3.5 text-accent-cyan" />
           Already have Access? 
           <Link to="/login" className="text-primary hover:text-white transition-colors">Authorize Here</Link>
        </div>
      </form>
    </AuthLayout>
  );
};

export default Register;
