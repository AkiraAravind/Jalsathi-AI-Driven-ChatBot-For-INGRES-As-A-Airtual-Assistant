import React, { useState } from 'react';

import { Mail, User, Building2, MapPin, ArrowRight, ShieldCheck, FileText } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import PortalAuthLayout from '../components/PortalAuthLayout';

const PortalRegister: React.FC = () => {
    const navigate = useNavigate();
    const [isLoading, setIsLoading] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        department: '',
        district: '',
        designation: ''
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...formData, role: 'official' })
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
                navigate('/portal/login', { state: { step: 'otp', email: formData.email } });
            } else {
          throw new Error(data.detail || data.message || `Official request failed (${response.status})`);
            }
        } catch (err) {
            alert(`[OFFICIAL_REG_ERROR] ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
            setIsLoading(false);
        }
    };

    return (
        <PortalAuthLayout title="Official Credential Request">
            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2 group">
                      <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1">Official Name</label>
                      <div className="relative">
                        <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                        <input 
                          required
                          type="text" 
                          placeholder="e.g. John Doe"
                          className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                          value={formData.name}
                          onChange={(e) => setFormData({...formData, name: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-2 group">
                      <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1">Gov E-Mail Vector</label>
                      <div className="relative">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                        <input 
                          required
                          type="email" 
                          placeholder="name@cgwb.gov.in"
                          className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                          value={formData.email}
                          onChange={(e) => setFormData({...formData, email: e.target.value})}
                        />
                      </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2 group">
                      <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1">Department Node</label>
                      <div className="relative">
                        <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                        <input 
                          required
                          type="text" 
                          placeholder="e.g. CGWB / SGWD"
                          className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                          value={formData.department}
                          onChange={(e) => setFormData({...formData, department: e.target.value})}
                        />
                      </div>
                    </div>
                    <div className="space-y-2 group">
                      <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1">Designation</label>
                      <div className="relative">
                        <FileText className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                        <input 
                          required
                          type="text" 
                          placeholder="e.g. Executive Engineer"
                          className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                          value={formData.designation}
                          onChange={(e) => setFormData({...formData, designation: e.target.value})}
                        />
                      </div>
                    </div>
                </div>

                <div className="space-y-2 group">
                  <label className="text-[10px] font-black uppercase tracking-widest text-accent-gold ml-1 transition-colors group-focus-within:text-accent-gold">Official Jurisdiction (District/State)</label>
                  <div className="relative">
                    <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-4 text-text-muted transition-colors group-focus-within:text-accent-gold" />
                    <input 
                      required
                      type="text" 
                      placeholder="e.g. Hyderabad, Telangana"
                      className="w-full bg-[#0d131f]/50 border-2 border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:border-accent-gold/40 transition-all font-bold placeholder:text-white/5"
                      value={formData.district}
                      onChange={(e) => setFormData({...formData, district: e.target.value})}
                    />
                  </div>
                </div>

                <button 
                    disabled={isLoading}
                    type="submit" 
                    className="w-full bg-accent-gold p-5 rounded-[1.25rem] text-sm font-black uppercase tracking-widest text-[#05070a] shadow-xl shadow-accent-gold/20 flex items-center justify-center gap-3 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 font-black italic"
                >
                    {isLoading ? <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin mx-auto" /> : <>SUBMIT ACCESS REQUEST <ShieldCheck className="w-5 h-5" /></>}
                </button>

                <div className="flex items-center justify-center gap-3 pt-4 text-xs font-bold text-text-muted opacity-60">
                   <ArrowRight className="w-4 h-4 text-accent-gold rotate-180" />
                   Return to <Link to="/portal/login" className="text-white hover:underline transition-all">Official Gate</Link>
                </div>
            </form>
        </PortalAuthLayout>
    );
};

export default PortalRegister;
