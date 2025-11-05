import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Paper,
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider,
  CircularProgress,
  Avatar,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Fade,
  Drawer,
  IconButton,
  ListSubheader,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Send as SendIcon,
  Psychology as PsychologyIcon,
  Person as PersonIcon,
  ExpandMore as ExpandMoreIcon,
  Article as ArticleIcon,
  Search as SearchIcon,
  Menu as MenuIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { apiHelpers, apiEndpoints } from '../services/api';
import ContextManagement from '../components/ContextManagement';
import { SourcesPanel } from '../components/SourcesPanel';
import { FocusedPapersBar } from '../components/FocusedPapersBar';
import { SourcesSidebar } from '../components/SourcesSidebar';
import '../styles/animations.css';

interface Source {
  arxiv_id: string;
  title: string;
  chunks_used: number;
  citation_count: number;
  is_seminal: boolean;
  is_foundational: boolean;
  cited_by_results: number;
  chunk_details?: Array<{
    section: string;
    text_preview: string;
    score: number;
  }>;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  searchResults?: SearchResult[];
  sessionInfo?: any;
  sources?: Source[];
  graph_insights?: {
    foundational_papers_added?: number;
    total_papers?: number;
    internal_citations?: number;
  };
}

interface SessionInfo {
  chat_id: string;
  status: string;
  current_strategy?: string;
  total_items?: number;
  user_turns?: number;
  synthetic_items?: number;
  [key: string]: any;
}

interface SearchResult {
  type: string;
  arxiv_id: string;
  title: string;
  section_title?: string;
  chunk_text: string;
  score: number;
  categories: string[];
  published_date: string;
}

const ResearchWorkspace: React.FC = () => {
  const [chatId, setChatId] = useState<string>('');
  const [isInitialized, setIsInitialized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m your research assistant. I can help you find relevant papers, analyze research, and explore academic literature. What would you like to know?',
      timestamp: new Date(),
    }
  ]);

  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationType, setConversationType] = useState<string>('research');
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [focusedPapers, setFocusedPapers] = useState<Array<{arxiv_id: string, title: string, citations?: number}>>([]);
  const [sourcesSidebarOpen, setSourcesSidebarOpen] = useState(false);
  const [selectedSources, setSelectedSources] = useState<Source[]>([]);
  const [chats, setChats] = useState<Array<{ id: string; name?: string | null; created_at?: string; updated_at?: string; turns?: number }>>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [newChatDialogOpen, setNewChatDialogOpen] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const loadSessionInfo = async () => {
    try {
      const result = await apiHelpers.getSessionInfo(chatId);
      if (result.success) {
        const sessionData = result.data.session_info || result.data;
        console.log('Session info loaded:', sessionData);
        setSessionInfo(sessionData);
      }
    } catch (error) {
      console.error('Failed to load session info:', error);
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
      messagesEndRef.current?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end',
        inline: 'nearest'
      });
    }, 100);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const result = await apiHelpers.checkHealth();
        setBackendStatus(result ? 'connected' : 'disconnected');
      } catch (error) {
        setBackendStatus('disconnected');
      }
    };
    checkBackendStatus();
  }, []);

  useEffect(() => {
    const savedFocusedPapers = sessionStorage.getItem(`focused_papers_${chatId}`);
    if (savedFocusedPapers) {
      try {
        setFocusedPapers(JSON.parse(savedFocusedPapers));
      } catch (error) {
        console.error('Failed to restore focused papers:', error);
      }
    }
  }, [chatId]);

  useEffect(() => {
    if (messages.length > 1) {
      sessionStorage.setItem(`chat_messages_${chatId}`, JSON.stringify(messages));
    }
  }, [messages, chatId]);


  useEffect(() => {
    sessionStorage.setItem(`focused_papers_${chatId}`, JSON.stringify(focusedPapers));
  }, [focusedPapers, chatId]);

  useEffect(() => {
    const initializeChat = async () => {
      try {
        const res = await apiHelpers.listChats();
        const existingChats = res.success ? (res.items || []) : [];
        setChats(existingChats);

        const savedChatId = sessionStorage.getItem('current_chat_id');
        
        if (savedChatId && existingChats.some((c: any) => c.id === savedChatId)) {
          setChatId(savedChatId);
          await loadMessages(savedChatId);
        } 
        else if (existingChats.length > 0) {
          const mostRecent = existingChats[0];
          setChatId(mostRecent.id);
          sessionStorage.setItem('current_chat_id', mostRecent.id);
          await loadMessages(mostRecent.id);
        } 
        else {
          const createRes = await apiHelpers.createChat();
          if (createRes.success && createRes.chat?.id) {
            const newChatId = createRes.chat.id;
            setChatId(newChatId);
            sessionStorage.setItem('current_chat_id', newChatId);
            setChats([createRes.chat]);
            setMessages([{
              id: '1',
              type: 'assistant',
              content: 'Hello! I\'m your research assistant. I can help you find relevant papers, analyze research, and explore academic literature. What would you like to know?',
              timestamp: new Date(),
            }]);
          }
        }
        
        setIsInitialized(true);
      } catch (error) {
        console.error('Failed to initialize chat:', error);
        setIsInitialized(true);
      }
    };

    initializeChat();
  }, []); // Run once on mount

  useEffect(() => {
    if (!isInitialized || !chatId) return;
    loadSessionInfo();
    loadFocusedPapers();
  }, [chatId, isInitialized]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        loadFocusedPapers();
      }
    };

    const handleFocus = () => {
      loadFocusedPapers();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, [chatId]);
  
  const loadFocusedPapers = async () => {
    try {
      const response = await apiEndpoints.getFocusedPapers(chatId);
      if (response.data && response.data.focused_papers) {
        const list = response.data.focused_papers as { arxiv_id: string; title: string }[];
        const seen = new Set<string>();
        const deduped: { arxiv_id: string; title: string }[] = [];
        for (const p of list) {
          if (!seen.has(p.arxiv_id)) {
            seen.add(p.arxiv_id);
            deduped.push(p);
          }
        }
        setFocusedPapers(deduped);
        sessionStorage.setItem(`focused_papers_${chatId}`, JSON.stringify(deduped));
      }
    } catch (error) {
      console.error('Failed to load focused papers:', error);
    }
  };
  
  const handleFocusPaper = async (arxivId: string, title: string) => {
    try {
      const alreadyFocused = focusedPapers.some(p => p.arxiv_id === arxivId);
      if (alreadyFocused) {
        await apiEndpoints.removeFocusedPaper(chatId, arxivId);
        const newFocusedPapers = focusedPapers.filter(p => p.arxiv_id !== arxivId);
        setFocusedPapers(newFocusedPapers);
        sessionStorage.setItem(`focused_papers_${chatId}`, JSON.stringify(newFocusedPapers));
        return;
      }

      await apiEndpoints.addFocusedPaper(chatId, { arxiv_id: arxivId, title });

      const newFocusedPapers = [...focusedPapers, { arxiv_id: arxivId, title }];
      setFocusedPapers(newFocusedPapers);
      sessionStorage.setItem(`focused_papers_${chatId}`, JSON.stringify(newFocusedPapers));
    } catch (error) {
      console.error('Failed to focus paper:', error);
    }
  };
  
  const handleUnfocusPaper = async (arxivId: string) => {
    try {
      await apiEndpoints.removeFocusedPaper(chatId, arxivId);
      
      const newFocusedPapers = focusedPapers.filter(p => p.arxiv_id !== arxivId);
      setFocusedPapers(newFocusedPapers);
      sessionStorage.setItem(`focused_papers_${chatId}`, JSON.stringify(newFocusedPapers));
    } catch (error) {
      console.error('Failed to unfocus paper:', error);
    }
  };
  
  const handleClearFocus = async () => {
    try {
      await apiEndpoints.clearFocusedPapers(chatId);
      setFocusedPapers([]);
    } catch (error) {
      console.error('Failed to clear focus:', error);
    }
  };

  const loadChats = async () => {
    try {
      const res = await apiHelpers.listChats();
      if (res.success) {
        setChats(res.items || []);
      }
    } catch (e) {
      console.error('Failed to load chats:', e);
    }
  };

  const handleSwitchChat = async (nextChatId: string) => {
    if (!nextChatId || nextChatId === chatId) return;
    sessionStorage.setItem('current_chat_id', nextChatId);
    setChatId(nextChatId);
    await loadMessages(nextChatId);
    await loadSessionInfo();
    await loadFocusedPapers();
  };

  const handleNewChat = () => {
    setNewChatDialogOpen(true);
  };

  const handleCreateChat = async () => {
    const chatName = newChatName.trim() || undefined;
    setNewChatDialogOpen(false);
    setNewChatName('');
    
    try {
      const res = await apiHelpers.createChat(chatName);
      if (res.success && res.chat?.id) {
        await loadChats();
        await handleSwitchChat(res.chat.id);
      } else {
        console.error('Failed to create chat:', res.error);
        alert('Failed to create chat. Please try again.');
      }
    } catch (error) {
      console.error('Error creating chat:', error);
      alert('Failed to create chat. Please try again.');
    }
  };

  const handleCancelNewChat = () => {
    setNewChatDialogOpen(false);
    setNewChatName('');
  };

  const loadMessages = async (chatIdToLoad: string) => {
    try {
      const res = await apiHelpers.getMessages(chatIdToLoad);
      if (res.success && res.messages) {
        const msgs = res.messages
          .slice()
          .reverse()
          .map((m: any) => ({
            id: m.id,
            type: m.role as 'user' | 'assistant',
            content: m.content,
            timestamp: new Date(m.created_at),
            sources: m.sources || [],
            graph_insights: m.graph_insights || {},
          }));
        setMessages(msgs);
      } else {
        setMessages([{
          id: '1', type: 'assistant', content: 'New chat started. How can I help?', timestamp: new Date(),
        }]);
      }
    } catch {
      setMessages([{
        id: '1', type: 'assistant', content: 'New chat started. How can I help?', timestamp: new Date(),
      }]);
    }
  };

  const handleOpenSources = (sources: Source[]) => {
    const normalizedSources = sources.map(source => ({
      ...source,
      chunk_details: source.chunk_details || []
    }));
    setSelectedSources(normalizedSources);
    setSourcesSidebarOpen(true);
  };

  const handleCloseSources = () => {
    setSourcesSidebarOpen(false);
  };

  const handleScroll = () => {
    // this for the future
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;
    const clientMsgId = `msg_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const userMessage: Message = {
      id: clientMsgId,
      type: 'user',
      content: currentMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const res = await apiHelpers.sendMessage(chatId, 'user', currentMessage, clientMsgId);
      
      if (res.success && res.message) {
        const assistantMessage: Message = {
          id: res.message.id,
          type: 'assistant',
          content: res.message.content,
          timestamp: new Date(res.message.created_at),
          sources: res.sources || [],
          graph_insights: res.graph_insights || {},
        };

        setMessages(prev => [...prev, assistantMessage]);
        await loadChats();
        
        if (res.sources && res.sources.length > 0) {
          setSelectedSources(res.sources);
        }
      } else {
        throw new Error(res.error || 'Failed to send message');
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message || 'Failed to connect to assistant'}. Please check if the backend is running on port 8000.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const renderSearchResults = (results: SearchResult[]) => {
    if (!results || results.length === 0) return null;

    return (
      <Accordion sx={{ mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SearchIcon color="primary" />
            <Typography variant="subtitle2">
              Search Results ({results.length} papers found)
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <List dense>
            {results.slice(0, 5).map((result, index) => (
              <React.Fragment key={index}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <ArticleIcon color="primary" fontSize="small" />
                        <Typography variant="subtitle2" component="span">
                          {result.title}
                        </Typography>
                        <Chip label={`Score: ${result.score.toFixed(3)}`} size="small" />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          arXiv ID: {result.arxiv_id} | {result.section_title || 'Full Paper'}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          {result.chunk_text.substring(0, 200)}...
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                          {result.categories.map((cat, catIndex) => (
                            <Chip key={catIndex} label={cat} size="small" variant="outlined" />
                          ))}
                        </Box>
                      </Box>
                    }
                  />
                </ListItem>
                {index < results.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box sx={{ 
      height: 'calc(100vh - 68px)', 
      display: 'flex', 
      flexDirection: 'column', 
      overflow: 'hidden',
      bgcolor: '#F8FAFC',
    }}>
      <Box sx={{ 
        bgcolor: '#FFFFFF',
        borderBottom: '1px solid rgba(15, 23, 42, 0.08)',
        px: { xs: 2, sm: 3, md: 4 },
        py: 2,
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <IconButton 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              size="small"
            >
              <MenuIcon />
            </IconButton>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ 
                width: 32, 
                height: 32, 
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <PsychologyIcon sx={{ color: 'white', fontSize: 18 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, fontSize: { xs: '0.95rem', sm: '1.1rem' }, color: '#0F172A' }}>
                  Research Assistant
                </Typography>
                {sessionInfo && (
                  <Box sx={{ display: { xs: 'none', sm: 'flex' }, gap: 0.75, mt: 0.25 }}>
                    <Chip 
                      size="small" 
                      label={`${sessionInfo.user_turns || 0} turns`}
                      sx={{ fontSize: '0.65rem', height: 18, bgcolor: 'rgba(37, 99, 235, 0.08)', color: '#1E40AF', fontWeight: 500 }}
                    />
                    <Chip 
                      size="small" 
                      label={sessionInfo.current_strategy || 'hybrid'}
                      sx={{ fontSize: '0.65rem', height: 18, textTransform: 'capitalize', bgcolor: 'rgba(37, 99, 235, 0.08)', color: '#1E40AF', fontWeight: 500 }}
                    />
                  </Box>
                )}
              </Box>
            </Box>
          </Box>
          
          <Box sx={{ display: { xs: 'none', sm: 'flex' }, gap: 0.75, bgcolor: '#F1F5F9', borderRadius: 2, p: 0.5 }}>
            {[
              { value: 'quick', label: 'Quick', icon: '⚡' },
              { value: 'research', label: 'Research', icon: '🔬' },
              { value: 'analysis', label: 'Analysis', icon: '📊' },
              { value: 'general', label: 'General', icon: '💬' },
            ].map((type) => (
              <Button
                key={type.value}
                variant="text"
                size="small"
                onClick={() => setConversationType(type.value)}
                disabled={isLoading}
                sx={{
                  borderRadius: 1.5,
                  textTransform: 'none',
                  fontWeight: 500,
                  fontSize: '0.8rem',
                  px: 2,
                  py: 0.75,
                  minWidth: { sm: '90px', md: '110px' },
                  color: conversationType === type.value ? '#2563EB' : '#64748B',
                  bgcolor: conversationType === type.value ? 'white' : 'transparent',
                  boxShadow: conversationType === type.value ? '0 1px 3px rgba(15,23,42,0.08)' : 'none',
                  '&:hover': {
                    bgcolor: conversationType === type.value ? 'white' : 'rgba(0,0,0,0.03)',
                  },
                }}
              >
                <Box component="span" sx={{ mr: 0.5, fontSize: '0.9rem' }}>{type.icon}</Box>
                <Box component="span">{type.label}</Box>
              </Button>
            ))}
          </Box>
        </Box>
      </Box>

      <Grid container spacing={0} sx={{ flexGrow: 1, height: 'calc(100% - 80px)', overflow: 'hidden' }}>
        {/* Left Sidebar: Chats */}
        <Grid
          item
          sx={{
            width: sidebarOpen ? 280 : 0,
            borderRight: '1px solid rgba(0,0,0,0.08)',
            bgcolor: 'white',
            display: { xs: 'none', md: 'flex' },
            flexDirection: 'column',
            transition: 'width 0.2s',
            overflow: 'hidden',
          }}
        >
          <Box sx={{ p: 2, borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
            <Button fullWidth variant="contained" onClick={handleNewChat}>New Chat</Button>
          </Box>
          <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
            <List dense>
              <ListSubheader>Chats</ListSubheader>
              {chats.map((c) => (
                <ListItem
                  button
                  selected={c.id === chatId}
                  onClick={() => handleSwitchChat(c.id)}
                  key={c.id}
                >
                  <ListItemText
                    primary={c.name || 'Unnamed Chat'}
                    secondary={c.updated_at ? new Date(c.updated_at).toLocaleString() : ''}
                    primaryTypographyProps={{ sx: { fontSize: '0.9rem', fontWeight: c.name ? 600 : 400, color: c.name ? '#1e293b' : '#94a3b8' } }}
                    secondaryTypographyProps={{ sx: { fontSize: '0.75rem' } }}
                  />
                </ListItem>
              ))}
            </List>
          </Box>
        </Grid>

        <Grid item xs sx={{ height: '100%', display: 'flex', borderRight: { lg: '1px solid rgba(0, 0, 0, 0.08)' } }}>
          <Box 
            sx={{ 
              flexGrow: 1,
              display: 'flex', 
              flexDirection: 'column',
              background: 'white',
              overflow: 'hidden',
            }}
          >

            <Box 
              ref={messagesContainerRef}
              onScroll={handleScroll}
              className="custom-scrollbar"
              sx={{ 
                flexGrow: 1, 
                overflow: 'auto',
                px: { xs: 2, sm: 3, md: 4 },
                py: 3,
                background: '#F8FAFC',
              }}
            >
              {/* Focused Papers Bar */}
              <FocusedPapersBar
                focusedPapers={focusedPapers}
                onRemove={handleUnfocusPaper}
                onClearAll={handleClearFocus}
              />
              
              {messages.map((message) => (
                <Fade in={true} timeout={300} key={message.id}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                      mb: 3,
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, maxWidth: { xs: '90%', sm: '85%', md: '75%' }, flexDirection: message.type === 'user' ? 'row-reverse' : 'row' }}>
                      {message.type === 'assistant' && (
                        <Avatar 
                          sx={{ 
                            background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                            width: 36, 
                            height: 36,
                            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
                            flexShrink: 0,
                          }}
                        >
                          <PsychologyIcon sx={{ fontSize: 20 }} />
                        </Avatar>
                      )}
                      
                      {message.type === 'user' && (
                        <Avatar 
                          sx={{ 
                            bgcolor: '#2563EB',
                            width: 36, 
                            height: 36,
                            boxShadow: '0 2px 8px rgba(37, 99, 235, 0.2)',
                            flexShrink: 0,
                          }}
                        >
                          <PersonIcon sx={{ fontSize: 20 }} />
                        </Avatar>
                      )}
                      
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Paper
                          elevation={0}
                          sx={{
                            p: { xs: 1.5, sm: 1.75 },
                            borderRadius: 2.5,
                            background: message.type === 'user' 
                              ? 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)'
                              : 'white',
                            color: message.type === 'user' ? 'white' : 'text.primary',
                            border: message.type === 'user' ? 'none' : '1px solid rgba(15, 23, 42, 0.08)',
                            boxShadow: 'none',
                            fontSize: { xs: '0.9rem', sm: '0.95rem' },
                            '& p': {
                              margin: 0,
                              lineHeight: 1.5,
                            },
                            '& p + p': {
                              marginTop: 0.75,
                            },
                          }}
                        >
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                          
                          {message.searchResults && renderSearchResults(message.searchResults)}
                        </Paper>
                        
                        {/* Sources Button - Opens Sidebar */}
                        {message.type === 'assistant' && message.sources && message.sources.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Button
                              variant="outlined"
                              size="small"
                              startIcon={<ArticleIcon />}
                              onClick={() => handleOpenSources(message.sources || [])}
                              sx={{
                                borderRadius: 2,
                                textTransform: 'none',
                                bgcolor: 'background.paper',
                                '&:hover': {
                                  bgcolor: 'primary.50',
                                  borderColor: 'primary.main',
                                },
                              }}
                            >
                              📚 View Sources ({message.sources.length} {message.sources.length === 1 ? 'paper' : 'papers'})
                            </Button>
                          </Box>
                        )}
                        
                        {/* Graph Insights Alert */}
                        {message.type === 'assistant' && message.graph_insights && message.graph_insights.foundational_papers_added && message.graph_insights.foundational_papers_added > 0 && (
                          <Box sx={{ mt: 1 }}>
                            <Paper elevation={0} sx={{ p: 1.5, bgcolor: 'info.50', border: '1px solid', borderColor: 'info.200' }}>
                              <Typography variant="caption" color="info.main">
                                💡 <strong>Graph Discovery:</strong> Added {message.graph_insights.foundational_papers_added} foundational paper(s) 
                                cited by {message.graph_insights.internal_citations || 'multiple'} papers in results
                              </Typography>
                            </Paper>
                          </Box>
                        )}
                        
                        <Typography 
                          variant="caption" 
                          sx={{ 
                            display: 'block',
                            mt: 0.5,
                            ml: 0.5,
                            fontSize: '0.7rem',
                            color: 'text.secondary',
                            opacity: 0.5,
                          }}
                        >
                          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </Fade>
              ))}
              
              {isLoading && (
                <Fade in={true}>
                  <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, maxWidth: { xs: '85%', sm: '80%', md: '70%' } }}>
                      <Avatar 
                        sx={{ 
                          background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                          width: 32, 
                          height: 32,
                          boxShadow: 'none',
                          flexShrink: 0,
                        }}
                        className="loading-pulse"
                      >
                        <PsychologyIcon sx={{ fontSize: 18 }} />
                      </Avatar>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Paper 
                          elevation={0}
                          sx={{ 
                            p: 1.75, 
                            bgcolor: 'white',
                            border: '1px solid rgba(15, 23, 42, 0.08)',
                            borderRadius: 2.5,
                          }}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <CircularProgress size={14} thickness={4} />
                            <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.95rem' }}>
                              Thinking...
                            </Typography>
                          </Box>
                        </Paper>
                      </Box>
                    </Box>
                  </Box>
                </Fade>
              )}
              
              <div ref={messagesEndRef} />
            </Box>

            <Box 
              sx={{ 
                p: { xs: 2, sm: 3 },
                borderTop: '1px solid rgba(15, 23, 42, 0.08)',
                background: '#FFFFFF',
                flexShrink: 0,
              }}
            >
              <Box sx={{ maxWidth: '1200px', margin: '0 auto' }}>
                <Box sx={{ display: 'flex', gap: { xs: 1.5, sm: 2 }, alignItems: 'flex-end' }}>
                  <Box sx={{ flex: 1, position: 'relative' }}>
                    <TextField
                      fullWidth
                      multiline
                      maxRows={5}
                      placeholder="💡 Ask me about research papers, methodologies, or any topic..."
                      value={currentMessage}
                      onChange={(e) => setCurrentMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      disabled={isLoading}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          bgcolor: 'white',
                          borderRadius: 2.5,
                          fontSize: { xs: '0.95rem', sm: '1rem' },
                          border: '1.5px solid rgba(15, 23, 42, 0.12)',
                          '& fieldset': {
                            border: 'none',
                          },
                          '&:hover': {
                            borderColor: 'rgba(37, 99, 235, 0.3)',
                            boxShadow: '0 2px 8px rgba(15, 23, 42, 0.04)',
                          },
                          '&.Mui-focused': {
                            borderColor: '#2563EB',
                            boxShadow: '0 0 0 3px rgba(37, 99, 235, 0.1)',
                          },
                          '& textarea': {
                            py: 1.5,
                            px: 2,
                          },
                        },
                      }}
                    />
                    {isLoading && (
                      <Box sx={{ position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)' }}>
                        <CircularProgress size={20} />
                      </Box>
                    )}
                  </Box>
                  <Button
                    onClick={handleSendMessage}
                    disabled={!currentMessage.trim() || isLoading}
                    variant="contained"
                    sx={{ 
                      background: 'linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)',
                      color: 'white',
                      minWidth: { xs: 48, sm: 56 },
                      height: { xs: 48, sm: 56 },
                      borderRadius: 2.5,
                      boxShadow: '0 2px 8px rgba(37, 99, 235, 0.25)',
                      '&:hover': {
                        background: 'linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)',
                        boxShadow: '0 4px 12px rgba(37, 99, 235, 0.35)',
                        transform: 'translateY(-1px)',
                      },
                      '&:disabled': {
                        background: '#E2E8F0',
                        color: '#94A3B8',
                        boxShadow: 'none',
                      },
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                  >
                    <SendIcon sx={{ fontSize: { xs: 20, sm: 22 } }} />
                  </Button>
                </Box>
                
                <Box sx={{ mt: 1.5, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
                    💡 Try: "Find papers about transformers" or "Analyze this paper"
                  </Typography>
                </Box>
              </Box>
            </Box>
          </Box>
        </Grid>

        <Grid item xs={12} lg={3} sx={{ 
          height: '100%', 
          overflow: 'auto', 
          display: { xs: 'none', lg: 'flex' }, 
          flexDirection: 'column',
          bgcolor: '#FFFFFF',
          borderLeft: '1px solid rgba(15, 23, 42, 0.08)',
          p: 2.5,
        }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Card sx={{ borderRadius: 3, boxShadow: 'none', border: '1px solid rgba(15, 23, 42, 0.1)', bgcolor: '#FFFFFF' }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, fontSize: '0.875rem', color: '#0F172A' }}>
                  ⚡ Quick Actions
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Button
                    fullWidth
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setMessages([{
                        id: '1',
                        type: 'assistant',
                        content: 'Session cleared! I\'m ready to help you with fresh research questions.',
                        timestamp: new Date(),
                      }]);
                      setSessionInfo(null);
                    }}
                    sx={{
                      borderRadius: 2,
                      textTransform: 'none',
                      justifyContent: 'flex-start',
                      fontSize: '0.875rem',
                      color: '#0F172A',
                      borderColor: 'rgba(15, 23, 42, 0.15)',
                      '&:hover': {
                        borderColor: '#2563EB',
                        bgcolor: 'rgba(37, 99, 235, 0.04)',
                      },
                    }}
                  >
                    🔄 Clear Session
                  </Button>
                </Box>
              </CardContent>
            </Card>

            <ContextManagement
              chatId={chatId}
              onStrategyChange={(strategy) => {
                console.log('Strategy changed to:', strategy);
                loadSessionInfo();
              }}
              onSessionClear={() => {
                setMessages([{
                  id: '1',
                  type: 'assistant',
                  content: 'Session cleared! I\'m ready to help you with fresh research questions.',
                  timestamp: new Date(),
                }]);
                setSessionInfo(null);
              }}
            />

            <Card sx={{ borderRadius: 3, boxShadow: 'none', border: '1px solid rgba(15, 23, 42, 0.1)', bgcolor: '#FFFFFF' }}>
              <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, fontSize: '0.875rem', color: '#0F172A' }}>
                  💡 Quick Prompts
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Button
                    fullWidth
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setCurrentMessage('Find papers about attention mechanisms in transformers');
                    }}
                    disabled={isLoading}
                    sx={{
                      borderRadius: 1.5,
                      textTransform: 'none',
                      justifyContent: 'flex-start',
                      fontSize: '0.8rem',
                      color: '#1D1D1F',
                      borderColor: '#D1D1D6',
                      '&:hover': {
                        borderColor: '#007AFF',
                        bgcolor: 'rgba(0, 122, 255, 0.04)',
                      },
                    }}
                  >
                    🔍 Attention Mechanisms
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setCurrentMessage('What are the latest developments in large language models?');
                    }}
                    disabled={isLoading}
                    sx={{
                      borderRadius: 1.5,
                      textTransform: 'none',
                      justifyContent: 'flex-start',
                      fontSize: '0.8rem',
                      color: '#1D1D1F',
                      borderColor: '#D1D1D6',
                      '&:hover': {
                        borderColor: '#007AFF',
                        bgcolor: 'rgba(0, 122, 255, 0.04)',
                      },
                    }}
                  >
                    🤖 Latest LLMs
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                    size="small"
                    onClick={() => {
                      setCurrentMessage('Explain computer vision methodologies');
                    }}
                    disabled={isLoading}
                    sx={{
                      borderRadius: 1.5,
                      textTransform: 'none',
                      justifyContent: 'flex-start',
                      fontSize: '0.8rem',
                      color: '#1D1D1F',
                      borderColor: '#D1D1D6',
                      '&:hover': {
                        borderColor: '#007AFF',
                        bgcolor: 'rgba(0, 122, 255, 0.04)',
                      },
                    }}
                  >
                    👁️ CV Methods
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Grid>
      </Grid>

      <Drawer
        anchor="right"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          '& .MuiDrawer-paper': {
            width: { xs: '85%', sm: '400px' },
            bgcolor: '#FFFFFF',
            p: 2.5,
          },
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600, color: '#0F172A' }}>
            Settings
          </Typography>
          <IconButton onClick={() => setDrawerOpen(false)}>
            <CloseIcon />
          </IconButton>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, fontSize: '0.875rem', color: '#0F172A' }}>
            Conversation Type
          </Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
            {[
              { value: 'quick', label: 'Quick', icon: '⚡' },
              { value: 'research', label: 'Research', icon: '🔬' },
              { value: 'analysis', label: 'Analysis', icon: '📊' },
              { value: 'general', label: 'General', icon: '💬' },
            ].map((type) => (
              <Button
                key={type.value}
                variant={conversationType === type.value ? 'contained' : 'outlined'}
                onClick={() => {
                  setConversationType(type.value);
                  setDrawerOpen(false);
                }}
                sx={{
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  p: 1.5,
                  ...(conversationType === type.value ? {
                    bgcolor: '#2563EB',
                    color: 'white',
                    '&:hover': { bgcolor: '#1E40AF' },
                  } : {
                    borderColor: 'rgba(15, 23, 42, 0.15)',
                    color: '#0F172A',
                    '&:hover': { borderColor: '#2563EB', bgcolor: 'rgba(37, 99, 235, 0.04)' },
                  }),
                }}
              >
                <Box component="span" sx={{ mr: 0.75, fontSize: '1.1rem' }}>{type.icon}</Box>
                {type.label}
              </Button>
            ))}
          </Box>
        </Box>

        <Card sx={{ borderRadius: 3, boxShadow: 'none', border: '1px solid rgba(15, 23, 42, 0.1)', mb: 2 }}>
          <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, fontSize: '0.875rem', color: '#0F172A' }}>
              ⚡ Quick Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button
                fullWidth
                variant="outlined"
                size="small"
                onClick={() => {
                  setMessages([{
                    id: '1',
                    type: 'assistant',
                    content: 'Session cleared! I\'m ready to help you with fresh research questions.',
                    timestamp: new Date(),
                  }]);
                  setSessionInfo(null);
                  setDrawerOpen(false);
                }}
                sx={{
                  borderRadius: 2,
                  textTransform: 'none',
                  justifyContent: 'flex-start',
                  fontSize: '0.875rem',
                  color: '#0F172A',
                  borderColor: 'rgba(15, 23, 42, 0.15)',
                  '&:hover': {
                    borderColor: '#2563EB',
                    bgcolor: 'rgba(37, 99, 235, 0.04)',
                  },
                }}
              >
                🔄 Clear Session
              </Button>
            </Box>
          </CardContent>
        </Card>

        <ContextManagement
          chatId={chatId}
          onStrategyChange={(strategy) => {
            console.log('Strategy changed to:', strategy);
          }}
          onSessionClear={() => {
            setMessages([{
              id: '1',
              type: 'assistant',
              content: 'Session cleared! I\'m ready to help you with fresh research questions.',
              timestamp: new Date(),
            }]);
            setSessionInfo(null);
            setDrawerOpen(false);
          }}
        />
      </Drawer>

      <SourcesSidebar
        open={sourcesSidebarOpen}
        onClose={handleCloseSources}
        sources={selectedSources as any}
        onFocusPaper={handleFocusPaper}
        focusedPapers={focusedPapers}
      />

      <Dialog 
        open={newChatDialogOpen} 
        onClose={handleCancelNewChat}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Chat</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Chat Name (optional)"
            type="text"
            fullWidth
            variant="outlined"
            value={newChatName}
            onChange={(e) => setNewChatName(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleCreateChat();
              }
            }}
            placeholder="e.g., Transformer Research, LLM Papers..."
            sx={{ mt: 2 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            You can leave this empty to create an unnamed chat, or give it a descriptive name.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelNewChat}>Cancel</Button>
          <Button onClick={handleCreateChat} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ResearchWorkspace;
