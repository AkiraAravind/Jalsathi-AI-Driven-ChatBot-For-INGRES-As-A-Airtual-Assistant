import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    LayoutGrid, 
    MessageSquare, 
    Info, 
    Phone, 
    Globe, 
    User, 
    Bell, 
    Search,
    ChevronDown,
    LogOut,
    ClipboardCheck
} from 'lucide-react';

interface Notification {
    id: string;
    title: string;
    message: string;
    time: string;
    read: boolean;
}

const TopNav: React.FC = () => {
    const location = useLocation();
    const [showNotifications, setShowNotifications] = useState(false);
    const [showProfileMenu, setShowProfileMenu] = useState(false);
    const [notifications] = useState<Notification[]>([
        { 
            id: '1', 
            title: 'Welcome to JalSathi', 
            message: 'Your hydrological expert system is ready.', 
            time: '2m ago', 
            read: false 
        },
        { 
            id: '2', 
            title: 'System Update', 
            message: 'GEC-2015 2024 analysis data integrated.', 
            time: '1h ago', 
            read: true 
        },
    ]);

    const [name, setName] = useState(localStorage.getItem('ingres_name') || 'Citizen');
    const [role, setRole] = useState(localStorage.getItem('ingres_role') || 'official');

    React.useEffect(() => {
        const handleProfileUpdate = () => {
            setName(localStorage.getItem('ingres_name') || 'Citizen');
            setRole(localStorage.getItem('ingres_role') || 'official');
        };
        window.addEventListener('profileUpdated', handleProfileUpdate);
        return () => window.removeEventListener('profileUpdated', handleProfileUpdate);
    }, []);

    const navItems = [
        { path: '/dashboard', label: 'AI ChatBOT', icon: MessageSquare },
        { path: '/dashboard/requirements', label: 'SIH Requirements', icon: ClipboardCheck },
        { path: '/dashboard/portal', label: 'Gov Portal', icon: Globe },
        { path: '/dashboard/about', label: 'About Project', icon: Info },
        { path: '/dashboard/contact', label: 'Support', icon: Phone },
    ];

    const unreadCount = notifications.filter(n => !n.read).length;

    return (
        <nav 
            className="h-20 w-full fixed top-0 left-0 px-8 flex items-center justify-between border-b border-white/5 backdrop-blur-xl bg-background/40"
            style={{ zIndex: 'var(--z-header)' }}
        >
            {/* Logo & Brand */}
            <Link to="/dashboard" className="flex items-center gap-3 group transition-transform hover:scale-105 active:scale-95">
                <div className="w-10 h-10 bg-primary/20 rounded-xl flex items-center justify-center border border-white/10 group-hover:border-primary/50 transition-colors">
                    <img src="/ingres-icon.png" alt="INGRES" className="w-6 h-6 object-contain" onError={(e) => { e.currentTarget.src = 'https://cdn-icons-png.flaticon.com/512/2099/2099192.png' }} />
                </div>
                <div>
                   <h1 className="text-lg font-black tracking-tighter text-white">INGRES</h1>
                   <p className="text-[9px] font-bold text-accent-cyan uppercase tracking-[0.3em] leading-none">Team JalSathi</p>
                </div>
            </Link>

            {/* Main Navigation */}
            <div className="hidden md:flex items-center gap-2">
                {navItems.map((item) => {
                    const isActive = location.pathname === item.path;
                    return (
                        <Link 
                            key={item.path}
                            to={item.path}
                            className={`px-4 py-2 rounded-xl flex items-center gap-2 text-xs font-bold transition-all duration-300 ${
                                isActive 
                                ? 'bg-primary/20 text-white border border-primary/40 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
                                : 'text-text-muted hover:text-white hover:bg-white/5'
                            }`}
                        >
                            <item.icon className={`w-4 h-4 ${isActive ? 'text-primary' : ''}`} />
                            {item.label}
                        </Link>
                    )
                })}
            </div>

            {/* Utility & Profile */}
            <div className="flex items-center gap-5">
                {/* Search Bar */}
                <div className="glass px-4 py-2 rounded-xl hidden lg:flex items-center gap-3 border-white/10 focus-within:border-primary/50 transition-all">
                   <Search className="w-4 h-4 text-text-muted" />
                   <input 
                     type="text" 
                     placeholder="Search hydrological data..." 
                     className="bg-transparent border-none text-xs font-bold outline-none placeholder:text-white/20 w-40 focus:w-56 transition-all"
                   />
                </div>

                {/* Notifications */}
                <div className="relative">
                    <motion.button 
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => { setShowNotifications(!showNotifications); setShowProfileMenu(false); }}
                      className={`relative p-2 rounded-xl transition-colors ${showNotifications ? 'bg-primary/20 text-white' : 'text-text-muted hover:text-white hover:bg-white/5'}`}
                    >
                        <Bell className="w-5 h-5" />
                        {unreadCount > 0 && (
                            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-accent-gold rounded-full border-2 border-background" />
                        )}
                    </motion.button>

                    <AnimatePresence>
                        {showNotifications && (
                            <motion.div 
                              initial={{ opacity: 0, y: 15, scale: 0.95 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: 15, scale: 0.95 }}
                               className="absolute top-[calc(100%+12px)] right-0 w-80 glass-card p-4 border border-white/10 origin-top-right"
                               style={{ zIndex: 'var(--z-dropdown)' }}
                            >
                                <div className="flex items-center justify-between mb-4 px-1">
                                    <h3 className="text-xs font-black uppercase tracking-widest text-text-muted">Notifications</h3>
                                    <span className="text-[10px] font-bold bg-primary/20 text-primary px-2 py-0.5 rounded-md">{unreadCount} New</span>
                                </div>
                                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                                    {notifications.map(n => (
                                        <div key={n.id} className={`p-3 rounded-xl border transition-colors cursor-pointer ${n.read ? 'border-white/5 opacity-60' : 'border-primary/20 bg-primary/5'}`}>
                                            <div className="flex justify-between items-start mb-1">
                                                <h4 className="text-[10px] font-black text-white uppercase">{n.title}</h4>
                                                <span className="text-[9px] text-text-muted">{n.time}</span>
                                            </div>
                                            <p className="text-[11px] text-text-muted leading-relaxed">{n.message}</p>
                                        </div>
                                    ))}
                                </div>
                                <button className="w-full mt-4 py-2 text-[10px] font-bold text-center text-primary hover:text-white transition-colors">View All Messages</button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <div className="h-6 w-px bg-white/10 hidden sm:block" />

                {/* Profile */}
                <div className="relative">
                    <motion.div 
                        whileHover={{ scale: 1.02 }}
                        onClick={() => { setShowProfileMenu(!showProfileMenu); setShowNotifications(false); }}
                        className="flex items-center gap-4 cursor-pointer p-1 pr-3 rounded-2xl hover:bg-white/5 transition-colors"
                    >
                        <div className="w-9 h-9 rounded-xl border-2 border-primary/40 p-0.5 shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                            <div className="w-full h-full rounded-lg bg-surface flex items-center justify-center text-primary overflow-hidden">
                                <User className="w-5 h-5" />
                            </div>
                        </div>
                        <div className="text-left hidden lg:block">
                            <p className="text-[10px] font-black tracking-tight text-white leading-none mb-1">{name}</p>
                            <div className="flex items-center gap-1">
                                <span className="w-1 h-1 rounded-full bg-accent-cyan pulse" />
                                <span className="text-[8px] font-bold text-text-muted uppercase tracking-widest">{role === 'official' ? 'Government Official' : (role === 'user' ? 'General User' : 'System Admin')}</span>
                            </div>
                        </div>
                        <ChevronDown className={`w-3 h-3 text-text-muted transition-transform duration-300 ${showProfileMenu ? 'rotate-180' : ''}`} />
                    </motion.div>

                    <AnimatePresence>
                        {showProfileMenu && (
                            <motion.div 
                              initial={{ opacity: 0, y: 15, scale: 0.95 }}
                              animate={{ opacity: 1, y: 0, scale: 1 }}
                              exit={{ opacity: 0, y: 15, scale: 0.95 }}
                               className="absolute top-[calc(100%+12px)] right-0 w-56 glass-card p-3 border border-white/10 origin-top-right overflow-hidden"
                               style={{ zIndex: 'var(--z-dropdown)' }}
                            >
                                <div className="p-3 mb-2 bg-white/5 rounded-xl border border-white/5">
                                    <p className="text-[9px] font-black uppercase tracking-widest text-text-muted mb-2">Vasavi College of Eng.</p>
                                    <div className="flex items-center gap-2 py-1 px-2 rounded-lg bg-primary/10 border border-primary/20">
                                        <LayoutGrid className="w-3 h-3 text-primary" />
                                        <span className="text-[10px] font-bold text-white">INGRES Node: Active</span>
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <Link to="/dashboard/profile" className="flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold text-text-muted hover:text-white hover:bg-primary/20 transition-all">
                                        <User className="w-4 h-4" />
                                        Edit Profile
                                    </Link>
                                    <button className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold text-text-muted hover:text-white hover:bg-primary/20 transition-all">
                                        <LayoutGrid className="w-4 h-4" />
                                        Source Repository
                                    </button>
                                    <div className="h-px bg-white/5 my-2" />
                                    <button 
                                        onClick={() => {
                                            localStorage.removeItem('ingres_token');
                                            localStorage.removeItem('ingres_role');
                                            localStorage.removeItem('ingres_name');
                                            window.location.href = '/login';
                                        }}
                                        className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold text-red-400 hover:bg-red-400/10 transition-all"
                                    >
                                        <LogOut className="w-4 h-4" />
                                        Disconnect Hub
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </nav>
    );
};

export default TopNav;
