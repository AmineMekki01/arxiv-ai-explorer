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
import { apiHelpers } from '../services/api';
import ContextManagement from '../components/ContextManagement';
import '../styles/animations.css';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  searchResults?: SearchResult[];
  sessionInfo?: any;
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
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m your AI research assistant. I can help you search through arXiv papers, analyze content, and provide insights. What would you like to research today?',
      timestamp: new Date(),
    }
  ]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatId] = useState(() => `chat_${Date.now()}`);
  const [conversationType, setConversationType] = useState<string>('research');
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [backendStatus, setBackendStatus] = useState<'unknown' | 'connected' | 'disconnected'>('unknown');
  const [drawerOpen, setDrawerOpen] = useState(false);
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
    loadSessionInfo();
  }, [chatId]);

  const handleScroll = () => {
    // this for the future
  };

  const handleSendMessage = async () => {
    if (!currentMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: currentMessage,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setIsLoading(true);

    try {
      const result = await apiHelpers.queryAssistant(currentMessage, chatId, conversationType);
      
      if (result.success) {
        const data = result.data;
        
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: data.final_output || data.content || 'I apologize, but I encountered an issue processing your request.',
          timestamp: new Date(),
          searchResults: data.search_results,
          sessionInfo: data.session_info,
        };

        setMessages(prev => [...prev, assistantMessage]);
        
        if (data.session_info) {
          setSessionInfo(data.session_info);
        }
      } else {
        throw new Error(result.error);
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
              sx={{ display: { xs: 'flex', lg: 'none' } }}
              onClick={() => setDrawerOpen(true)}
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
        <Grid item xs={12} lg={9} sx={{ height: '100%', display: 'flex', borderRight: { lg: '1px solid rgba(0, 0, 0, 0.08)' } }}>
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
    </Box>
  );
};

export default ResearchWorkspace;
