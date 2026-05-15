import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Phone, 
    Mail, 
    MapPin, 
    ExternalLink, 
    ShieldCheck,
    Send,
    CheckCircle2,
    MessageSquare,
    AlertCircle
} from 'lucide-react';

const ContactSection: React.FC = () => {
    const [formState, setFormState] = useState<'idle' | 'sending' | 'success'>('idle');
    const [formData, setFormData] = useState({ name: '', email: '', message: '' });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormState('sending');
        
        try {
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            if (data.status === 'success') {
                setFormState('success');
                setFormData({ name: '', email: '', message: '' });
                setTimeout(() => setFormState('idle'), 5000);
            } else {
                throw new Error('Feedback relay failed');
            }
        } catch (err) {
            alert('[SYSTEM_ERROR] Could not relay feedback. Attempting local log...');
            console.log('Feedback log:', formData);
            setFormState('idle');
        }
    };

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-6xl pb-20"
        >
            <div className="text-center mb-16 relative">
                <h2 className="text-5xl font-serif font-black mb-6 italic tracking-tight text-white">Get in Touch</h2>
                <p className="mt-2 text-text-muted text-xl font-medium max-w-2xl mx-auto leading-relaxed">
                    Direct Support for <span className="text-white">Project INGRES</span> & Team JalSathi
                </p>
                <div className="absolute -top-10 left-1/2 -translate-x-1/2 w-40 h-40 bg-accent-gold/5 blur-[80px] rounded-full pointer-events-none" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
                {/* Contact Information */}
                <div className="lg:col-span-5 space-y-8">
                    <div className="glass-card p-8 group hover:bg-primary/5 transition-all">
                        <div className="flex items-center gap-6">
                            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shadow-lg">
                                <Phone className="w-6 h-6" />
                            </div>
                            <div>
                                <h4 className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-1">Direct Line</h4>
                                <p className="text-2xl font-serif font-black text-white">+91 8121500540</p>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-8 group hover:bg-accent-violet/5 transition-all">
                        <div className="flex items-center gap-6">
                            <div className="w-14 h-14 rounded-2xl bg-accent-violet/10 flex items-center justify-center text-accent-violet shadow-lg">
                                <Mail className="w-6 h-6" />
                            </div>
                            <div>
                                <h4 className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-1">Correspondence</h4>
                                <p className="text-xl font-bold text-white break-all">1akiraaravind1@gmail.com</p>
                            </div>
                        </div>
                    </div>

                    <div className="glass-card p-8 group hover:bg-accent-cyan/5 transition-all">
                        <div className="flex items-center gap-6">
                            <div className="w-14 h-14 rounded-2xl bg-accent-cyan/10 flex items-center justify-center text-accent-cyan shadow-lg">
                                <MapPin className="w-6 h-6" />
                            </div>
                            <div>
                                <h4 className="text-[10px] font-black uppercase tracking-widest text-text-muted mb-1">Location Hub</h4>
                                <p className="text-xl font-bold text-white">Vasavi College of Eng. / IITH</p>
                            </div>
                        </div>
                    </div>

                    <div className="p-8 border border-white/5 bg-white/[0.02] rounded-3xl">
                        <div className="flex gap-4 items-center mb-6">
                            <ShieldCheck className="w-5 h-5 text-accent-gold" />
                            <h5 className="text-xs font-black uppercase tracking-widest text-white">System Links</h5>
                        </div>
                        <div className="space-y-4">
                            <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-all group">
                                <span className="text-[11px] font-bold text-text-muted group-hover:text-white transition-colors">Official INGRES Portal</span>
                                <ExternalLink className="w-3 h-3 text-white/20 group-hover:text-white" />
                            </a>
                            <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-all group">
                                <span className="text-[11px] font-bold text-text-muted group-hover:text-white transition-colors">CGWB Chatbot Website</span>
                                <ExternalLink className="w-3 h-3 text-white/20 group-hover:text-white" />
                            </a>
                            <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-all group">
                                <span className="text-[11px] font-bold text-text-muted group-hover:text-white transition-colors">Dummy Gov Portal (V1)</span>
                                <ExternalLink className="w-3 h-3 text-white/20 group-hover:text-white" />
                            </a>
                        </div>
                    </div>
                </div>

                {/* Feedback Form */}
                <div className="lg:col-span-7">
                    <div className="glass-card p-10 relative overflow-hidden h-full">
                        <AnimatePresence mode="wait">
                            {formState === 'success' ? (
                                <motion.div 
                                    key="success"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    className="h-full flex flex-col items-center justify-center text-center py-20"
                                >
                                    <div className="w-20 h-20 rounded-3xl bg-green-500/20 flex items-center justify-center text-green-500 mb-8 shadow-2xl shadow-green-500/20">
                                        <CheckCircle2 className="w-10 h-10" />
                                    </div>
                                    <h3 className="text-2xl font-bold mb-4">Feedback Transmitted</h3>
                                    <p className="text-text-muted text-sm max-w-sm">Thank you for your response. Your data has been encrypted and sent to 1akiraaravind1@gmail.com.</p>
                                </motion.div>
                            ) : (
                                <motion.form 
                                    key="form"
                                    onSubmit={handleSubmit}
                                    className="space-y-6"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                >
                                    <div className="flex items-center gap-3 mb-8">
                                        <MessageSquare className="w-5 h-5 text-primary" />
                                        <h3 className="text-xl font-bold tracking-tight">Direct Feedback</h3>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1">Your Name</label>
                                            <input 
                                                required
                                                value={formData.name}
                                                onChange={(e) => setFormData({...formData, name: e.target.value})}
                                                type="text" 
                                                placeholder="e.g. John Doe"
                                                className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm outline-none focus:border-primary/50 transition-all placeholder:text-white/10"
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1">Email Address</label>
                                            <input 
                                                required
                                                value={formData.email}
                                                onChange={(e) => setFormData({...formData, email: e.target.value})}
                                                type="email" 
                                                placeholder="e.g. name@department.gov.in"
                                                className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm outline-none focus:border-primary/50 transition-all placeholder:text-white/10"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black uppercase tracking-widest text-text-muted ml-1">How can we improve INGRES?</label>
                                        <textarea 
                                            required
                                            value={formData.message}
                                            onChange={(e) => setFormData({...formData, message: e.target.value})}
                                            rows={6}
                                            placeholder="Tell us about issues, data gaps, or feature requests..."
                                            className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 text-sm outline-none focus:border-primary/50 transition-all placeholder:text-white/10 resize-none"
                                        />
                                    </div>

                                    <div className="pt-4 flex items-center justify-between">
                                        <div className="flex items-center gap-2 text-[9px] font-bold text-text-muted/60 bg-white/5 px-3 py-2 rounded-lg border border-white/5">
                                            <AlertCircle className="w-3 h-3" />
                                            SSL Encrypted Transmission
                                        </div>
                                        <button 
                                            disabled={formState === 'sending'}
                                            type="submit"
                                            className="px-8 py-4 bg-primary text-white rounded-2xl text-sm font-black flex items-center gap-3 shadow-xl shadow-primary/20 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                                        >
                                            {formState === 'sending' ? (
                                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            ) : (
                                                <>
                                                    SEND FEEDBACK
                                                    <Send className="w-4 h-4" />
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </motion.form>
                            )}
                        </AnimatePresence>
                        
                        <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-primary/5 blur-[120px] rounded-full pointer-events-none" />
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default ContactSection;
