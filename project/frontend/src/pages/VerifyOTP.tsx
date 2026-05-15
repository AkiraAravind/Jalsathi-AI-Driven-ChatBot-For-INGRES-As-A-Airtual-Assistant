import React, { useState, useEffect } from 'react';

import { ShieldCheck, ArrowLeft, Send } from 'lucide-react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import AuthLayout from '../components/AuthLayout';

const VerifyOTP: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [isVerifying, setIsVerifying] = useState(false);
  const [timer, setTimer] = useState(300);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimer((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleChange = (index: number, value: string) => {
    if (value.length > 1) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    
    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      nextInput?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      prevInput?.focus();
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = otp.join('');
    if (code.length < 6) return;

    setIsVerifying(true);
    try {
      const response = await fetch('/api/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: state?.email, otp: code })
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
        // Store session and role
        localStorage.setItem('ingres_token', data.token);
        localStorage.setItem('ingres_role', data.role || 'user');
        localStorage.setItem('ingres_user', state?.email || 'authenticated_user');
        if (data.name) {
          localStorage.setItem('ingres_name', data.name);
        }
        window.dispatchEvent(new Event('profileUpdated'));
        
        navigate('/dashboard');
      } else {
        throw new Error(data.detail || data.message || `Verification failed (${response.status})`);
      }
    } catch (err) {
      alert(`[AUTH_GATE_ERROR] ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (!state?.email) return;
    try {
      const response = await fetch('/api/auth/resend-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: state.email })
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
        alert("A new neural code has been dispatched.");
        setTimer(300);
      } else {
        alert(data.detail || data.message || `Failed to resend code (${response.status})`);
      }
    } catch (err) {
      alert("Error resending code.");
    }
  };

  return (
    <AuthLayout title="Verify Access" subtitle={`Neural Code sent to ${state?.email || 'your email'}`}>
      <div className="flex flex-col items-center">
        <form onSubmit={handleVerify} className="w-full space-y-10">
          <div className="flex justify-between gap-3">
            {otp.map((digit, index) => (
              <input
                key={index}
                id={`otp-${index}`}
                type="text"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="w-12 h-16 bg-white/5 border border-white/10 rounded-2xl text-center text-2xl font-black text-primary outline-none focus:border-primary/50 transition-all font-mono shadow-inner"
              />
            ))}
          </div>

          <div className="text-center">
            <p className="text-[10px] font-bold text-text-muted uppercase tracking-widest mb-2">Code Lifecycle</p>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/5 text-[11px] font-black text-accent-cyan">
              {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')} UNTIL_EXPIRE
            </div>
          </div>

          <button 
            disabled={isVerifying || otp.some(d => !d)}
            type="submit"
            className="w-full bg-primary p-4 rounded-2xl text-sm font-black uppercase tracking-widest text-white shadow-xl shadow-primary/20 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
          >
            {isVerifying ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mx-auto" />
            ) : 'VERIFY & AUTHORIZE'}
          </button>

          <div className="flex items-center justify-between px-2">
            <Link to="/register" className="flex items-center gap-2 text-[10px] font-black text-text-muted hover:text-white transition-colors uppercase tracking-widest">
                <ArrowLeft className="w-3.5 h-3.5" />
                Change Email
            </Link>
            <button 
                type="button"
                onClick={handleResend}
                className="flex items-center gap-2 text-[10px] font-black text-primary hover:underline transition-colors uppercase tracking-widest"
            >
                Resend Code
                <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>

        <div className="mt-10 flex items-center gap-2 p-4 bg-accent-gold/5 rounded-2xl border border-accent-gold/10">
           <ShieldCheck className="w-5 h-5 text-accent-gold" />
           <p className="text-[10px] font-bold text-text-muted leading-tight">Your access is strictly encrypted via GEC-2015 security protocols. Do not share your code.</p>
        </div>
      </div>
    </AuthLayout>
  );
};

export default VerifyOTP;
