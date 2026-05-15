import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Droplets, ShieldCheck, TrendingUp, ArrowRight } from 'lucide-react';

const Landing: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="relative min-h-screen w-full overflow-hidden flex flex-col items-center justify-center">
            {/* Immersive 3D Background Elements based on GitHub sample atmospheric effects */}
            <div className="absolute inset-0 z-0">
                <motion.div
                    animate={{ scale: [1, 1.2, 1], x: [0, 50, 0], y: [0, 30, 0] }}
                    transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                    className="absolute -top-[10%] -left-[10%] w-[60%] h-[60%] bg-primary/10 rounded-full blur-[120px]"
                />
                <motion.div
                    animate={{ scale: [1.2, 1, 1.2], x: [0, -40, 0], y: [0, -50, 0] }}
                    transition={{ duration: 15, repeat: Infinity, ease: 'linear' }}
                    className="absolute -bottom-[20%] -right-[10%] w-[70%] h-[70%] bg-accent-violet/10 rounded-full blur-[150px]"
                />
                {/* Floating Mesh Background Grid */}
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-50 mix-blend-overlay" />
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#1E293B_1px,transparent_1px),linear-gradient(to_bottom,#1E293B_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20" />
            </div>

            <main className="relative z-10 max-w-7xl mx-auto px-6 text-center">
                <motion.div
                    initial={{ opacity: 0, y: 50, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
                >
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass border-white/10 mb-8 animate-float">
                        <span className="w-2 h-2 rounded-full bg-accent-cyan shadow-[0_0_8px_#22D3EE]" />
                        <span className="text-xs font-bold tracking-widest text-accent-cyan uppercase">Project INGRES — AI Integrated</span>
                    </div>

                    <h1 className="text-6xl md:text-8xl font-serif font-extrabold tracking-tight mb-8">
                        The Future of <br />
                        <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent-cyan via-primary to-accent-violet">
                            Hydrological Intelligence
                        </span>
                    </h1>

                    <p className="max-w-2xl mx-auto text-xl text-text-muted mb-12 leading-relaxed">
                        Precision groundwater assessment using V-JEPA predictive architecture and sub-district level data mapping.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
                        <button
                            onClick={() => navigate('/auth')}
                            className="btn-primary group flex items-center gap-3 text-lg"
                        >
                            Explore Dashboard
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                        <button className="px-8 py-3 rounded-full border border-white/10 text-lg hover:bg-white/5 transition-colors">
                            About GEC Methodology
                        </button>
                    </div>
                </motion.div>

                {/* Showcase Cards with Floating Effect */}
                <div className="mt-32 grid grid-cols-1 md:grid-cols-3 gap-8">
                    {[
                        { icon: Droplets, title: "Precision Mapping", desc: "Block-level sub-district data for all 36 States/UTs." },
                        { icon: TrendingUp, title: "JEPA Prediction", desc: "V-JEPA predictive trajectory for at-risk districts." },
                        { icon: ShieldCheck, title: "Manual Search", desc: "Instant retrieval of GEC-2015 methodology rules." }
                    ].map((feature, i) => (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: i * 0.2, duration: 0.8 }}
                            className="glass-card p-8 group overflow-hidden"
                        >
                            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6 text-primary group-hover:bg-primary group-hover:text-white transition-colors duration-500">
                                <feature.icon className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                            <p className="text-text-muted text-sm leading-relaxed">{feature.desc}</p>
                            <div className="absolute top-0 right-0 -mr-4 -mt-4 w-24 h-24 bg-primary/5 rounded-full blur-2xl group-hover:bg-primary/20 transition-all duration-700" />
                        </motion.div>
                    ))}
                </div>
            </main>

            <footer className="relative z-10 w-full mt-32 py-12 border-t border-white/5 flex flex-col items-center">
                <div className="text-text-muted text-xs tracking-widest uppercase mb-4">Developed by TBP Team for SIH 2025/26</div>
                <div className="flex gap-8 text-sm text-text-muted italic">
                    <span>Ministry of Jal Shakti</span>
                    <span>CGWB</span>
                    <span>IIT Hyderabad</span>
                </div>
            </footer>
        </div>
    );
};

export default Landing;
