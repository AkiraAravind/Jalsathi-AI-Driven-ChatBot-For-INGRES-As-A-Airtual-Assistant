import React from 'react';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Info, 
  Phone, 
  ExternalLink, 
  Database,
  Globe,
  LogOut
} from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';

const Sidebar: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { id: 'chat', label: 'AI ChatBOT', icon: MessageSquare, path: '/dashboard' },
        { id: 'about', label: 'About Project', icon: Info, path: '/dashboard/about' },
        { id: 'contact', label: 'Contact Support', icon: Phone, path: '/dashboard/contact' },
    ];

    const externalLinks = [
        { label: 'Official INGRES', icon: Globe, url: 'https://ingres.iith.ac.in' },
        { label: 'Gov Data Portal', icon: Database, url: 'https://data.gov.in' },
    ];

    return (
        <motion.aside 
            initial={{ x: -100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="w-72 h-screen glass border-r border-white/5 flex flex-col p-6 z-30 relative"
        >
            {/* Project Branding */}
            <div className="flex items-center gap-3 mb-12 px-2">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-accent-cyan flex items-center justify-center shadow-lg shadow-primary/20">
                    <LayoutDashboard className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-black tracking-tight leading-tight">INGRES</h1>
                    <span className="text-[10px] font-bold text-accent-cyan tracking-widest uppercase">Expert System</span>
                </div>
            </div>

            {/* Main Navigation */}
            <nav className="flex-1 space-y-2">
                <p className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-4 ml-2">Intelligence Hub</p>
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => navigate(item.path)}
                        className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 group ${
                            location.pathname === item.path 
                            ? 'bg-primary/20 text-white border border-primary/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
                            : 'text-text-muted hover:bg-white/5 hover:text-white'
                        }`}
                    >
                        <item.icon className={`w-5 h-5 ${location.pathname === item.path ? 'text-accent-cyan' : 'group-hover:text-primary'} transition-colors`} />
                        <span className="text-sm font-semibold tracking-wide">{item.label}</span>
                        {location.pathname === item.path && (
                            <motion.div layoutId="active-nav" className="ml-auto w-1.5 h-1.5 rounded-full bg-accent-cyan shadow-[0_0_8px_#22D3EE]" />
                        )}
                    </button>
                ))}

                <div className="pt-8 pb-4">
                    <p className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-4 ml-2">External Portals</p>
                    <div className="space-y-2">
                        {externalLinks.map((link) => (
                            <a
                                key={link.label}
                                href={link.url}
                                target="_blank"
                                rel="noreferrer"
                                className="w-full flex items-center gap-4 px-4 py-3 rounded-xl text-text-muted hover:bg-white/5 hover:text-white transition-all text-sm group"
                            >
                                <link.icon className="w-5 h-5 group-hover:text-accent-gold" />
                                <span className="font-semibold">{link.label}</span>
                                <ExternalLink className="w-3 h-3 ml-auto opacity-0 group-hover:opacity-60" />
                            </a>
                        ))}
                    </div>
                </div>
            </nav>

            {/* Sidebar Footer */}
            <div className="pt-6 border-t border-white/5">
                <button 
                  onClick={() => navigate('/auth')}
                  className="w-full flex items-center gap-4 px-4 py-3 rounded-xl text-red-400/60 hover:bg-red-400/10 hover:text-red-400 transition-all text-sm font-bold"
                >
                    <LogOut className="w-5 h-5" />
                    Logout Session
                </button>
            </div>
            
            {/* Background Texture Logic from Sole Reaper sample */}
            <div className="absolute bottom-0 left-0 w-full h-32 bg-primary/5 [mask-image:linear-gradient(to_top,black,transparent)] pointer-events-none" />
        </motion.aside>
    );
};

export default Sidebar;
