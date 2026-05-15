import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, CheckCircle2, ArrowRight, ShieldCheck, ExternalLink, Globe } from 'lucide-react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import PortalAuthLayout from '../components/PortalAuthLayout';

const PortalLogin: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const [step, setStep] = useState<'email' | 'otp'>(location.state?.step || 'email');
    const [email, setEmail] = useState(location.state?.email || '');
    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [isLoading, setIsLoading] = useState(false);

    const handleEmailSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, role: 'official' })
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
                setStep('otp');
            } else {
                throw new Error(data.detail || data.message || `Official access request failed (${response.status})`);
            }
        } catch (err) {
            alert(`[OFFICIAL_GATE_ERROR] ${err instanceof Error ? err.message : 'Unknown error'}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        const code = otp.join('');
        if (code.length < 6) return;

        setIsLoading(true);
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp: code })
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
                localStorage.setItem('ingres_role', data.role || 'official');
                localStorage.setItem('ingres_user', email);
                if (data.name) {
                    localStorage.setItem('ingres_name', data.name);
                }
                window.dispatchEvent(new Event('profileUpdated'));
                
                navigate('/dashboard/portal');
            } else {
                throw new Error(data.detail || data.message || `Official Key Invalid (${response.status})`);
            }
        } catch (err) {
            alert(`[OFFICIAL_GATE_DENIED] ${err instanceof Error ? err.message : 'Invalid Key'}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleOtpChange = (index: number, value: string) => {
        if (value.length > 1) return;
        const newOtp = [...otp];
        newOtp[index] = value;
        setOtp(newOtp);
        if (value && index < 5) {
            document.getElementById(`p-otp-${index+1}`)?.focus();
        }
    };

    return (
        <PortalAuthLayout title="Government Official Access Hub">
            <AnimatePresence mode="wait">
                {step === 'email' ? (
                    <motion.form 
                        key="email-step"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        onSubmit={handleEmailSubmit} 
                        className="space-y-6"
                    >
                        <div className="space-y-3 group">
                          <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1">Official E-Mail Vector</label>
                          <div className="relative">
                            <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-5 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                            <input 
                              required
                              type="email" 
                              placeholder="johndoe@cgwb.gov.in"
                              className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-[1.25rem] py-5 pl-14 pr-6 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                            />
                          </div>
                        </div>

                        <button 
                            disabled={isLoading}
                            type="submit" 
                            className="w-full bg-accent-gold p-5 rounded-[1.25rem] text-sm font-black uppercase tracking-widest text-[#05070a] shadow-xl shadow-accent-gold/20 flex items-center justify-center gap-3 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
                        >
                            {isLoading ? <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" /> : <>INITIATE SECURE SESSION <ArrowRight className="w-5 h-5" /></>}
                        </button>

                        <div className="flex items-center justify-center gap-3 pt-4 text-xs font-bold text-text-muted opacity-60">
                           <ShieldCheck className="w-4 h-4 text-accent-gold" />
                           Not Registered? <Link to="/portal/register" className="text-white hover:underline transition-all">Request Official Credentials</Link>
                        </div>
                        
                        <div className="p-5 bg-white/5 rounded-2xl border border-white/5 flex items-center gap-4 group cursor-pointer hover:bg-white/10 transition-all">
                           <Globe className="w-5 h-5 text-accent-cyan" />
                           <div className="flex-1">
                              <p className="text-[10px] font-black uppercase tracking-widest text-white">Central Ground Water Board</p>
                              <p className="text-[9px] font-bold text-text-muted leading-tight">Official GEC-2015 Reporting Framework</p>
                           </div>
                           <ExternalLink className="w-3 h-3 text-white/20 group-hover:text-white" />
                        </div>
                    </motion.form>
                ) : (
                    <motion.form 
                        key="otp-step"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        onSubmit={handleVerify} 
                        className="space-y-8 text-center"
                    >
                        <div className="flex justify-between gap-3">
                            {otp.map((digit, i) => (
                                <input
                                    key={i}
                                    id={`p-otp-${i}`}
                                    type="text"
                                    maxLength={1}
                                    value={digit}
                                    onChange={(e) => handleOtpChange(i, e.target.value)}
                                    className="w-12 h-16 bg-[#0d131f]/50 border-2 border-white/5 rounded-[1rem] text-center text-2xl font-black text-accent-gold outline-none focus:border-accent-gold/40 transition-all"
                                />
                            ))}
                        </div>
                        
                        <div className="p-6 bg-accent-gold/5 rounded-[1.5rem] border border-accent-gold/10">
                            <p className="text-[10px] font-bold text-accent-gold uppercase tracking-widest mb-2 font-black italic">Verification Key Sent</p>
                            <p className="text-[11px] text-text-muted leading-relaxed font-bold">Please check your official government email for the 6-digit cryptographic key.</p>
                        </div>

                        <button 
                            disabled={isLoading}
                            type="submit" 
                            className="w-full bg-accent-gold p-5 rounded-[1.25rem] text-sm font-black uppercase tracking-widest text-[#05070a] shadow-xl shadow-accent-gold/20 flex items-center justify-center gap-3 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 font-black italic"
                        >
                             {isLoading ? <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" /> : <>VERIFY_OFFICIAL_GATE <CheckCircle2 className="w-5 h-5" /></>}
                        </button>
                        
                        <button type="button" onClick={() => setStep('email')} className="text-[10px] font-black uppercase tracking-widest text-text-muted hover:text-white transition-all">Back to Access Gate</button>
                    </motion.form>
                )}
            </AnimatePresence>
        </PortalAuthLayout>
    );
};

export default PortalLogin;
