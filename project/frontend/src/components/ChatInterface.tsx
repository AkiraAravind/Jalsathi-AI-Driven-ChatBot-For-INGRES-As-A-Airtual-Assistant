import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, 
    Bot, 
    User, 
    Sparkles, 
    Quote, 
    Languages, 
    Maximize2, 
    Minimize2, 
    Clock,
    ChevronLeft,
    ChevronRight,
    MessageSquare,
    History,
    Upload,
    Download
} from 'lucide-react';
import { chatService } from '../services/api';
import type { ChatStreamFinalEvent } from '../services/api';
import ChartComponent from './ChartComponent';
import ReactMarkdown from 'react-markdown';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: string[];
    chart?: any;
    language?: string;
}

interface ChatSession {
    id: string;
    title: string;
    date: string;
    messages: Message[];
}

const ChatInterface: React.FC = () => {
    const getUserScope = () => {
        const user = localStorage.getItem('ingres_user') || localStorage.getItem('ingres_name') || 'guest';
        return user.toLowerCase().replace(/[^a-z0-9]/g, '_');
    };

    const generateSessionId = () => `session_${getUserScope()}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    const [isOnline, setIsOnline] = React.useState(navigator.onLine);

    React.useEffect(() => {
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    const [messages, setMessages] = useState<Message[]>(() => {
        return [{
            id: '1',
            role: 'assistant',
            content: "Welcome to INGRES AI. I am your expert system for India's groundwater resources. How can I assist you today?",
            language: 'en'
        }];
    });
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [showHistory, setShowHistory] = useState(true);
    const [sessionId, setSessionId] = useState<string>(generateSessionId());
    const [uploadedContext, setUploadedContext] = useState<string>('');
    const [uploadedFileName, setUploadedFileName] = useState<string>('');
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    
    const fileInputRef = useRef<HTMLInputElement>(null);
    
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const data = await chatService.getHistory();
                setSessions(data);
            } catch (err) {
                console.error("Failed to load history", err);
            }
        };
        fetchHistory();
    }, []);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        // Reset input so the same file can be re-selected if needed
        e.target.value = '';

        setIsUploading(true);
        try {
            const context = await chatService.uploadFile(file);
            // Don't fire a chat bubble — just store context + filename as a badge
            setUploadedContext(context);
            setUploadedFileName(file.name);
        } catch (error: any) {
            const msg = error?.response?.data?.detail || 'Only PDF and TXT files are supported.';
            alert(`Upload failed: ${msg}`);
        } finally {
            setIsUploading(false);
        }
    };

    const handleExport = async () => {
        try {
            const exportMessages = messages.map((m) => ({
                role: m.role,
                content: m.content,
                citations: m.citations || [],
            }));
            const blob = await chatService.downloadChatPdf(sessionId, exportMessages);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ingres-chat-${sessionId}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (error: any) {
            const status = error?.response?.status;
            const detail = error?.response?.data?.detail;
            alert(`Failed to download chat PDF.${status ? ` (HTTP ${status})` : ''}${detail ? ` ${detail}` : ''}`);
        }
    };

    const handleSessionSelect = (session: ChatSession) => {
        setSessionId(session.id);
        const transformedMessages: Message[] = session.messages.map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            citations: m.citations,
            chart: m.chart,
            language: m.language
        }));
        setMessages(transformedMessages);
    };

    const handleNewChat = () => {
        setSessionId(generateSessionId());
        setMessages([{
            id: '1',
            role: 'assistant',
            content: "Started a new exploration session. How can I assist you?",
            language: 'en'
        }]);
        setUploadedContext('');
        setUploadedFileName('');
    };

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        // Build display content — if there's a file attached, note it beneath the query
        const displayContent = uploadedFileName
            ? `${input}\n\n📎 *${uploadedFileName}*`
            : input;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: displayContent,
        };

        setMessages(prev => [...prev, userMsg]);
        const currentContext = uploadedContext;
        const currentInput = input;
        setInput('');
        // Clear the file badge immediately after submission
        setUploadedContext('');
        setUploadedFileName('');
        setIsLoading(true);

        try {
            const assistantId = (Date.now() + 1).toString();
            setMessages(prev => [...prev, {
                id: assistantId,
                role: 'assistant',
                content: '',
                citations: [],
            }]);

            await chatService.streamMessage(currentInput, sessionId, currentContext || undefined, {
                onToken: (token) => {
                    setMessages(prev => prev.map((m) => (
                        m.id === assistantId
                            ? { ...m, content: `${m.content}${token}` }
                            : m
                    )));
                },
                onFinal: (event: ChatStreamFinalEvent) => {
                    setMessages(prev => prev.map((m) => (
                        m.id === assistantId
                            ? {
                                ...m,
                                content: event.answer || m.content,
                                citations: event.citations,
                                chart: event.chart,
                                language: event.language,
                            }
                            : m
                    )));
                },
                onError: (message) => {
                    setMessages(prev => prev.map((m) => (
                        m.id === assistantId
                            ? { ...m, content: message || 'Streaming error occurred.' }
                            : m
                    )));
                },
            });
        } catch (error: any) {
            const status = error?.response?.status;
            const detail = error?.response?.data?.detail;
            const msg = status === 401
                ? "Session expired or unauthorized. Please login again to continue."
                : (detail || "Error connecting to INGRES Intelligence. Please verify backend and API configuration.");
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: msg
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className={`flex h-full transition-all duration-500 ease-in-out ${isFullscreen ? 'fixed inset-4 z-[200] bg-background' : 'relative rounded-3xl'} overflow-hidden border border-white/5 shadow-2xl backdrop-blur-md`}>
            
            {/* Internal History Sidebar */}
            <AnimatePresence>
                {showHistory && (
                    <motion.div 
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 240, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        className="h-full border-r border-white/5 bg-white/[0.02] flex flex-col overflow-hidden"
                    >
                        <div className="p-6 border-b border-white/5 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <History className="w-4 h-4 text-primary" />
                                <span className="text-[10px] font-black uppercase tracking-widest text-text-muted">Recent Intelligence</span>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-hide">
                            <button onClick={handleNewChat} className="w-full flex items-center gap-3 p-3 rounded-xl bg-primary/10 border border-primary/30 text-[11px] font-bold text-white transition-all hover:bg-primary/20 mb-4">
                                <MessageSquare className="w-4 h-4" />
                                New Exploration
                            </button>
                            {sessions.map(s => (
                                <button key={s.id} onClick={() => handleSessionSelect(s)} className={`w-full group text-left p-3 rounded-xl border transition-all ${sessionId === s.id ? 'bg-primary/20 border-primary/30' : 'hover:bg-white/5 border-transparent hover:border-white/5'}`}>
                                    <h4 className="text-[11px] font-bold text-text-muted group-hover:text-white transition-colors truncate">{s.title}</h4>
                                    <span className="text-[9px] text-white/20 font-bold">{s.date}</span>
                                </button>
                            ))}
                        </div>
                        <div className="p-4 border-t border-white/5">
                           <div className={`flex items-center gap-2 text-[9px] font-bold uppercase tracking-widest transition-colors ${isOnline ? 'text-accent-cyan/80' : 'text-red-500/80'}`}>
                               <Clock className="w-3 h-3" />
                               {isOnline ? 'Cloud Sync Active' : 'Cloud Sync Offline'}
                           </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col h-full bg-background/20 relative">
                {/* Header */}
                <div className="px-8 py-5 border-b border-white/5 flex items-center justify-between glass sticky top-0 z-20">
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => setShowHistory(!showHistory)}
                            className="p-2 mr-2 rounded-lg hover:bg-white/5 text-text-muted hover:text-white transition-colors"
                        >
                            {showHistory ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                        <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center text-primary shadow-[0_0_15px_rgba(59,130,246,0.2)]">
                            <Bot className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="font-bold tracking-tight text-white/90">INGRES AI Core</h3>
                            <div className="flex items-center gap-1.5">
                                <motion.span 
                                    animate={{ opacity: [1, 0.4, 1] }} 
                                    transition={{ duration: 1.5, repeat: Infinity }} 
                                    className="w-1.5 h-1.5 rounded-full bg-accent-cyan" 
                                />
                                <span className="text-[10px] font-black text-accent-cyan uppercase tracking-widest">Hydrological Link Active</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={handleExport} className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] uppercase tracking-widest font-bold text-text-muted hover:bg-white/10 hover:text-white transition-colors">
                            <Download className="w-3 h-3 text-accent-green" />
                            PDF
                        </button>
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-[10px] uppercase tracking-widest font-bold text-text-muted">
                            <Languages className="w-3 h-3 text-primary" />
                            Multi-Lingual
                        </div>
                        <button 
                            onClick={() => setIsFullscreen(!isFullscreen)}
                            className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-text-muted hover:text-white hover:bg-primary/20 transition-all"
                        >
                            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                        </button>
                    </div>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-hide">
                    <AnimatePresence initial={false}>
                        {messages.map((msg) => (
                            msg.chart ? (
                            <div
                                key={msg.id}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`max-w-[92%] group ${msg.role === 'user' ? 'flex flex-row-reverse' : 'flex'} gap-4`}>
                                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center border border-white/10 ${
                                        msg.role === 'user' ? 'bg-accent-violet/20 text-accent-violet shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 'bg-primary/20 text-primary shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                    }`}>
                                        {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                    </div>
                                    <div className="space-y-4">
                                        <div className={`px-6 py-4 rounded-2xl glass border border-white/5 ${
                                            msg.role === 'user' ? 'bg-primary/10 rounded-tr-none' : 'bg-surface/40 rounded-tl-none'
                                        }`}>
                                            <div className="text-sm leading-relaxed whitespace-pre-wrap flex flex-col gap-2 [&>p]:m-0 [&>ul]:list-disc [&>ul]:ml-4 [&>h1]:font-bold [&>h2]:font-bold [&>h3]:font-bold">
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                        </div>
                                        
                                        {/* Chart Rendering logic */}
                                        {msg.chart && (
                                            <div className="mt-4">
                                                <div className="flex items-center gap-2 text-accent-gold mb-2 ml-2">
                                                    <Sparkles className="w-4 h-4" />
                                                    <span className="text-xs font-bold uppercase tracking-widest">Scientific Visualization</span>
                                                </div>
                                                <ChartComponent data={msg.chart} />
                                            </div>
                                        )}

                                        {/* Citations Box */}
                                        {msg.citations && msg.citations.length > 0 && (
                                            <div className="flex flex-wrap gap-2 mt-2 ml-2">
                                                {msg.citations.map((cite, i) => (
                                                    <div key={i} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/5 text-[9px] font-bold text-text-muted hover:bg-white/10 transition-colors">
                                                        <Quote className="w-2 h-2 opacity-50" />
                                                        {cite}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                            ) : (
                            <motion.div
                                key={msg.id}
                                initial={{ opacity: 0, y: 20, scale: 0.98 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`max-w-[92%] group ${msg.role === 'user' ? 'flex flex-row-reverse' : 'flex'} gap-4`}>
                                    <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center border border-white/10 ${
                                        msg.role === 'user' ? 'bg-accent-violet/20 text-accent-violet shadow-[0_0_15px_rgba(139,92,246,0.1)]' : 'bg-primary/20 text-primary shadow-[0_0_15px_rgba(59,130,246,0.1)]'
                                    }`}>
                                        {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                                    </div>
                                    <div className="space-y-4">
                                        <div className={`px-6 py-4 rounded-2xl glass border border-white/5 ${
                                            msg.role === 'user' ? 'bg-primary/10 rounded-tr-none' : 'bg-surface/40 rounded-tl-none'
                                        }`}>
                                            <div className="text-sm leading-relaxed whitespace-pre-wrap flex flex-col gap-2 [&>p]:m-0 [&>ul]:list-disc [&>ul]:ml-4 [&>h1]:font-bold [&>h2]:font-bold [&>h3]:font-bold">
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                        </div>

                                        {/* Citations Box */}
                                        {msg.citations && msg.citations.length > 0 && (
                                            <div className="flex flex-wrap gap-2 mt-2 ml-2">
                                                {msg.citations.map((cite, i) => (
                                                    <div key={i} className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/5 text-[9px] font-bold text-text-muted hover:bg-white/10 transition-colors">
                                                        <Quote className="w-2 h-2 opacity-50" />
                                                        {cite}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                            )
                        ))}
                        {isLoading && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                                <div className="glass px-6 py-4 rounded-2xl rounded-tl-none border-white/5">
                                    <div className="flex gap-2">
                                        {[1, 2, 3].map(i => (
                                            <motion.div 
                                              key={i} 
                                              animate={{ y: [0, -5, 0] }} 
                                              transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }} 
                                              className="w-1.5 h-1.5 bg-primary/40 rounded-full" 
                                            />
                                        ))}
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Bar */}
                <div className="p-8 relative z-20">
                    {/* Pending file badge — shown above input when a file is staged */}
                    {uploadedFileName && (
                        <motion.div
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 6 }}
                            className="mb-3 flex items-center gap-2 px-4 py-2 rounded-xl bg-accent-green/10 border border-accent-green/20 w-fit"
                        >
                            <Upload className="w-3.5 h-3.5 text-accent-green" />
                            <span className="text-[11px] font-bold text-accent-green truncate max-w-[220px]">{uploadedFileName}</span>
                            <span className="text-[10px] text-text-muted">— staged. Type your query and hit Send.</span>
                            <button
                                type="button"
                                onClick={() => { setUploadedContext(''); setUploadedFileName(''); }}
                                className="ml-1 text-text-muted hover:text-red-400 transition-colors text-[11px] font-black"
                            >✕</button>
                        </motion.div>
                    )}
                    <form onSubmit={handleSend} className="relative group">
                        <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full opacity-0 group-focus-within:opacity-30 transition-opacity duration-700" />
                        <div className="glass flex items-center p-2 rounded-2xl border-white/10 relative shadow-2xl">
                            <input 
                                type="file" 
                                ref={fileInputRef} 
                                className="hidden" 
                                accept=".pdf,.txt"
                                onChange={handleFileUpload}
                            />
                            <button 
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={isUploading}
                                title={isUploading ? 'Uploading...' : 'Attach PDF or TXT'}
                                className={`p-3 transition-colors ${
                                    uploadedFileName ? 'text-accent-green' : 'text-text-muted hover:text-white'
                                } ${isUploading ? 'opacity-50 cursor-not-allowed animate-pulse' : ''}`}
                            >
                                <Upload className="w-5 h-5" />
                            </button>
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                placeholder={uploadedFileName ? `Ask about "${uploadedFileName}"...` : 'Ask about district trends, GEC formulas, or categorization...'}
                                className="flex-1 bg-transparent px-2 py-3 text-sm font-medium outline-none placeholder:text-white/20"
                            />
                            <button
                                type="submit"
                                disabled={!input.trim() || isLoading}
                                className={`p-3 rounded-xl transition-all ${
                                    !input.trim() || isLoading 
                                    ? 'bg-white/5 text-white/20 cursor-not-allowed' 
                                    : 'bg-primary text-white shadow-lg shadow-primary/20 hover:scale-105 active:scale-95'
                                }`}
                            >
                                <Send className="w-5 h-5" />
                            </button>
                        </div>
                    </form>
                    <div className="mt-4 flex justify-center items-center gap-1.5">
                        <span className="text-[9px] font-black tracking-[0.2em] text-text-muted opacity-40 uppercase">GEC-2015 Hydrological Logic Pulse</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatInterface;
