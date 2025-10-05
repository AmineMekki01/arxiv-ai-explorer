import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Tooltip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Info as InfoIcon,
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Psychology as PsychologyIcon,
  ExpandMore as ExpandMoreIcon,
  Refresh as RefreshIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { apiHelpers } from '../services/api';
import '../styles/animations.css';

interface ContextManagementProps {
  chatId: string;
  onStrategyChange?: (strategy: string) => void;
  onSessionClear?: () => void;
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

interface Strategy {
  description: string;
  pros: string[];
  cons: string[];
  best_for: string;
}

interface Strategies {
  [key: string]: Strategy;
}

const ContextManagement: React.FC<ContextManagementProps> = ({
  chatId,
  onStrategyChange,
  onSessionClear,
}) => {
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [strategies, setStrategies] = useState<Strategies>({});
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [showDetails, setShowDetails] = useState(false);
  const [showStrategiesDialog, setShowStrategiesDialog] = useState(false);

  const loadSessionInfo = async () => {
    try {
      const result = await apiHelpers.getSessionInfo(chatId);
      if (result.success) {
        setSessionInfo(result.data.session_info);
        setSelectedStrategy(result.data.session_info.current_strategy || 'hybrid');
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to load session info');
    }
  };

  const loadStrategies = async () => {
    try {
      const result = await apiHelpers.getStrategies();
      if (result.success) {
        setStrategies(result.data.strategies);
      }
    } catch (err) {
      console.error('Failed to load strategies:', err);
    }
  };

  useEffect(() => {
    loadSessionInfo();
    loadStrategies();
  }, [chatId]);

  const handleStrategyChange = async (newStrategy: string) => {
    setLoading(true);
    setError('');

    try {
      const result = await apiHelpers.switchContextStrategy(chatId, newStrategy);
      if (result.success) {
        setSelectedStrategy(newStrategy);
        await loadSessionInfo();
        onStrategyChange?.(newStrategy);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to switch strategy');
    } finally {
      setLoading(false);
    }
  };

  const handleClearSession = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await apiHelpers.clearSession(chatId);
      if (result.success) {
        await loadSessionInfo();
        onSessionClear?.();
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError('Failed to clear session');
    } finally {
      setLoading(false);
    }
  };

  const getStrategyIcon = (strategy: string) => {
    switch (strategy) {
      case 'trimming':
        return <SpeedIcon />;
      case 'summarization':
        return <MemoryIcon />;
      case 'hybrid':
        return <PsychologyIcon />;
      default:
        return <SettingsIcon />;
    }
  };

  return (
    <Card 
      sx={{
        borderRadius: 3,
        boxShadow: 'none',
        border: '1px solid rgba(15, 23, 42, 0.1)',
        bgcolor: '#FFFFFF',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="subtitle2" sx={{ display: 'flex', alignItems: 'center', gap: 1, fontWeight: 600, fontSize: '0.875rem', color: '#0F172A' }}>
            <SettingsIcon sx={{ color: 'primary.main', fontSize: 20 }} />
            Context Management
          </Typography>
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            <Tooltip title="Refresh session info">
              <IconButton 
                size="small" 
                onClick={loadSessionInfo}
                sx={{
                  '&:hover': {
                    background: 'rgba(37, 99, 235, 0.08)',
                    transform: 'rotate(90deg)',
                  },
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="View strategy details">
              <IconButton 
                size="small" 
                onClick={() => setShowStrategiesDialog(true)}
                sx={{
                  '&:hover': {
                    background: 'rgba(37, 99, 235, 0.08)',
                  },
                  transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              >
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Current Strategy */}
        <Box sx={{ mb: 2.5 }}>
          <Typography variant="caption" gutterBottom sx={{ fontWeight: 600, color: '#64748B', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Current Strategy
          </Typography>
          {sessionInfo && sessionInfo.status !== 'no_session' ? (
            <Chip
              icon={getStrategyIcon(sessionInfo.current_strategy || 'hybrid')}
              label={sessionInfo.current_strategy || 'hybrid'}
              sx={{ 
                textTransform: 'capitalize',
                fontWeight: 500,
                px: 1.5,
                py: 1.25,
                borderRadius: 2,
                bgcolor: 'rgba(37, 99, 235, 0.1)',
                color: '#1E40AF',
                fontSize: '0.8125rem',
              }}
            />
          ) : (
            <Box sx={{ 
              p: 1.5, 
              borderRadius: 2, 
              bgcolor: 'rgba(217, 119, 6, 0.08)',
              border: '1px solid rgba(217, 119, 6, 0.2)',
            }}>
              <Typography variant="caption" sx={{ color: '#D97706', fontSize: '0.75rem' }}>
                💬 Send a message first to create a session
              </Typography>
            </Box>
          )}
        </Box>

        {/* Strategy Selector */}
        <Box sx={{ mb: 2.5 }}>
          <FormControl 
            fullWidth 
            size="small"
            disabled={!sessionInfo || sessionInfo.status === 'no_session'}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
                '&:hover fieldset': {
                  borderColor: '#2563EB',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#2563EB',
                },
                '&.Mui-focused': {
                  boxShadow: '0 0 0 3px rgba(37, 99, 235, 0.1)',
                },
              },
            }}
          >
            <InputLabel>Switch Strategy</InputLabel>
            <Select
              value={selectedStrategy}
              label="Switch Strategy"
              onChange={(e) => handleStrategyChange(e.target.value)}
              disabled={loading || !sessionInfo || sessionInfo.status === 'no_session'}
            >
              <MenuItem value="trimming">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SpeedIcon fontSize="small" />
                  Trimming (Fast)
                </Box>
              </MenuItem>
              <MenuItem value="summarization">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MemoryIcon fontSize="small" />
                  Summarization (Memory)
                </Box>
              </MenuItem>
              <MenuItem value="hybrid">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <PsychologyIcon fontSize="small" />
                  Hybrid (Adaptive)
                </Box>
              </MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Session Stats */}
        {sessionInfo && sessionInfo.status === 'active' && (
          <Accordion sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2">Session Statistics</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Total Messages"
                    secondary={sessionInfo.total_items || 0}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="User Turns"
                    secondary={sessionInfo.user_turns || 0}
                  />
                </ListItem>
                {sessionInfo.synthetic_items !== undefined && (
                  <ListItem>
                    <ListItemText
                      primary="Summarized Items"
                      secondary={sessionInfo.synthetic_items}
                    />
                  </ListItem>
                )}
                {sessionInfo.trim_threshold && (
                  <ListItem>
                    <ListItemText
                      primary="Trim Threshold"
                      secondary={sessionInfo.trim_threshold}
                    />
                  </ListItem>
                )}
                {sessionInfo.summary_threshold && (
                  <ListItem>
                    <ListItemText
                      primary="Summary Threshold"
                      secondary={sessionInfo.summary_threshold}
                    />
                  </ListItem>
                )}
              </List>
            </AccordionDetails>
          </Accordion>
        )}

        {/* Actions */}
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            color="error"
            size="small"
            startIcon={<ClearIcon />}
            onClick={handleClearSession}
            disabled={loading}
            fullWidth
            sx={{
              borderRadius: 2,
              fontWeight: 500,
              fontSize: '0.875rem',
              '&:hover': {
                background: 'rgba(220, 38, 38, 0.08)',
                transform: 'translateY(-1px)',
              },
              transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            Clear Session
          </Button>
        </Box>

        {/* Strategy Details Dialog */}
        <Dialog
          open={showStrategiesDialog}
          onClose={() => setShowStrategiesDialog(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>Context Management Strategies</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Choose the right strategy based on your conversation needs:
            </Typography>

            {Object.entries(strategies).map(([strategyName, strategy]) => (
              <Accordion key={strategyName} sx={{ mb: 1 }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStrategyIcon(strategyName)}
                    <Typography variant="h6" sx={{ textTransform: 'capitalize' }}>
                      {strategyName}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {strategy.description}
                  </Typography>

                  <Typography variant="subtitle2" color="success.main" gutterBottom>
                    Pros:
                  </Typography>
                  <List dense>
                    {strategy.pros.map((pro, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={`• ${pro}`} />
                      </ListItem>
                    ))}
                  </List>

                  <Typography variant="subtitle2" color="warning.main" gutterBottom>
                    Cons:
                  </Typography>
                  <List dense>
                    {strategy.cons.map((con, index) => (
                      <ListItem key={index}>
                        <ListItemText primary={`• ${con}`} />
                      </ListItem>
                    ))}
                  </List>

                  <Typography variant="subtitle2" gutterBottom>
                    Best for:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {strategy.best_for}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowStrategiesDialog(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default ContextManagement;
