import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, User, ArrowRight, Shield } from 'lucide-react';

const Auth: React.FC = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        // Simulate loading sequence before redirect
        setTimeout(() => {
            navigate('/dashboard');
        }, 1500);
    };

    return (
        <div className="min-h-screen w-full bg-background flex items-center justify-center relative overflow-hidden px-6">
            {/* Background Atmosphere */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-0 right-0 w-[50%] h-[50%] bg-primary/5 blur-[100px]" />
                <div className="absolute bottom-0 left-0 w-[50%] h-[50%] bg-accent-gold/5 blur-[100px]" />
            </div>

            {/* Geometric Loading Overlay (Inspired by GitHub sample intro-box) */}
            <AnimatePresence>
                {isLoading && (
                    <motion.div
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        exit={{ scaleY: 0 }}
                        className="fixed inset-0 z-[100] bg-primary flex items-center justify-center transform-origin-bottom"
                    >
                        <motion.h2 
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-4xl font-serif font-black text-white italic"
                        >
                            INGRES OS 
                        </motion.h2>
                    </motion.div>
                )}
            </AnimatePresence>

            <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                className="relative z-10 w-full max-w-md"
            >
                {/* 3D Glassmorphic Form Card */}
                <div className="glass-card p-10 relative overflow-hidden backdrop-blur-3xl group">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-accent-cyan to-accent-violet" />
                    
                    <div className="flex items-center gap-3 mb-12">
                        <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary border border-primary/20 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
                            <Shield className="w-6 h-6" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold tracking-tight">INGRES Access</h2>
                            <p className="text-xs text-text-muted font-bold tracking-[0.2em] uppercase opacity-60">National Resource Expert System</p>
                        </div>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <AnimatePresence mode="wait">
                            {!isLogin && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0, y: -20 }}
                                    animate={{ opacity: 1, height: 'auto', y: 0 }}
                                    exit={{ opacity: 0, height: 0, y: -20 }}
                                    className="space-y-2 overflow-hidden"
                                >
                                    <label className="text-sm font-semibold text-text-muted ml-1">Full Name</label>
                                    <div className="relative group">
                                        <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted group-focus-within:text-primary transition-colors" />
                                        <input
                                            type="text"
                                            placeholder="John Doe"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 focus:ring-2 focus:ring-primary/20 focus:border-primary/40 outline-none transition-all placeholder:text-white/20 text-sm"
                                        />
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-text-muted ml-1">Work Email</label>
                            <div className="relative group">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted group-focus-within:text-primary transition-colors" />
                                <input
                                    type="email"
                                    required
                                    placeholder="name@organization.gov.in"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 focus:ring-2 focus:ring-primary/20 focus:border-primary/40 outline-none transition-all placeholder:text-white/20 text-sm font-medium"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between ml-1">
                                <label className="text-sm font-semibold text-text-muted">Password</label>
                                {isLogin && <button type="button" className="text-xs text-primary font-bold hover:underline">Forgot?</button>}
                            </div>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted group-focus-within:text-primary transition-colors" />
                                <input
                                    type="password"
                                    required
                                    placeholder="••••••••"
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 focus:ring-2 focus:ring-primary/20 focus:border-primary/40 outline-none transition-all placeholder:text-white/20 text-sm"
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full btn-primary h-12 flex items-center justify-center gap-3 mt-4"
                        >
                            {isLoading ? "Authenticating..." : isLogin ? "Secure Entry" : "Create Account"}
                            {!isLoading && <ArrowRight className="w-4 h-4" />}
                        </button>
                    </form>

                    <div className="mt-8 pt-8 border-t border-white/5 text-center">
                        <button
                            type="button"
                            onClick={() => setIsLogin(!isLogin)}
                            className="text-sm text-text-muted hover:text-white transition-colors"
                        >
                            {isLogin ? "New to the project? " : "Already registered? "}
                            <span className="text-accent-gold font-bold">{isLogin ? "Request Access" : "Login Now"}</span>
                        </button>
                    </div>

                    {/* Decorative Glow Elements from user's sample */}
                    <div className="absolute -bottom-12 -right-12 w-24 h-24 bg-primary/20 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-1000" />
                </div>

                <div className="mt-12 flex items-center justify-center gap-8 text-white/20 grayscale opacity-50 hover:grayscale-0 hover:opacity-100 transition-all duration-700">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/8/84/Government_of_India_logo.svg" alt="GOI" className="h-8 brightness-0 invert" />
                    <img src="https://upload.wikimedia.org/wikipedia/en/thumb/1/19/IIT_Hyderabad_Logo.svg/1200px-IIT_Hyderabad_Logo.svg.png" alt="IITH" className="h-8 rounded" />
                </div>
            </motion.div>
        </div>
    );
};

export default Auth;
