import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Chip,
  Alert,
  Collapse,
  Fade,
} from '@mui/material';
import {
  Speed as SpeedIcon,
  Psychology as PsychologyIcon,
  Analytics as AnalyticsIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { apiEndpoints } from '../services/api';
import '../styles/animations.css';

interface ConversationTypeSelectorProps {
  value: string;
  onChange: (type: string) => void;
  disabled?: boolean;
}

interface Recommendation {
  strategy: string;
  description: string;
  benefits: string[];
  [key: string]: any;
}

const ConversationTypeSelector: React.FC<ConversationTypeSelectorProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  const [recommendations, setRecommendations] = useState<Record<string, Recommendation>>({});
  const [showDetails, setShowDetails] = useState(false);
  const [loading, setLoading] = useState(false);

  const conversationTypes = [
    {
      value: 'quick',
      label: 'Quick Query',
      icon: <SpeedIcon />,
      description: 'Fast, independent questions',
      color: 'success',
    },
    {
      value: 'research',
      label: 'Research',
      icon: <PsychologyIcon />,
      description: 'Deep exploration and discovery',
      color: 'primary',
    },
    {
      value: 'analysis',
      label: 'Analysis',
      icon: <AnalyticsIcon />,
      description: 'Detailed paper analysis',
      color: 'info',
    },
    {
      value: 'general',
      label: 'General',
      icon: <SettingsIcon />,
      description: 'Mixed conversation types',
      color: 'default',
    },
  ];

  const loadRecommendations = useCallback(async (type: string) => {
    if (recommendations[type]) return;

    setLoading(true);
    try {
      const response = await apiEndpoints.getStrategyRecommendations(type);
      setRecommendations(prev => ({
        ...prev,
        [type]: response.data.recommendations,
      }));
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  }, [recommendations]);

  useEffect(() => {
    loadRecommendations(value);
  }, [value, loadRecommendations]);

  const handleChange = (event: React.MouseEvent<HTMLElement>, newType: string | null) => {
    if (newType !== null) {
      onChange(newType);
      loadRecommendations(newType);
    }
  };

  const currentType = conversationTypes.find(type => type.value === value);
  const currentRecommendation = recommendations[value];

  return (
    <Card 
      className="glass-card"
      sx={{
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.3)',
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>💬 Conversation Type</Typography>
          <Tooltip title="Show details">
            <InfoIcon
              sx={{ 
                cursor: 'pointer', 
                opacity: 0.7,
                color: 'primary.main',
                '&:hover': {
                  opacity: 1,
                  transform: 'scale(1.1)',
                },
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
              }}
              onClick={() => setShowDetails(!showDetails)}
            />
          </Tooltip>
        </Box>

        <ToggleButtonGroup
          value={value}
          exclusive
          onChange={handleChange}
          disabled={disabled}
          sx={{ 
            display: 'grid', 
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, 
            gap: { xs: 1, sm: 1.5 },
            width: '100%',
            '& .MuiToggleButton-root': {
              border: '2px solid',
              borderColor: 'rgba(0, 0, 0, 0.08)',
              borderRadius: 2.5,
              textTransform: 'none',
              flexDirection: 'column',
              padding: { xs: 1.5, sm: 2 },
              height: 'auto',
              minHeight: { xs: '80px', sm: 'auto' },
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                borderColor: 'primary.main',
                background: 'rgba(0, 122, 255, 0.05)',
                transform: 'translateY(-2px)',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
              },
              '&.Mui-selected': {
                borderColor: 'primary.main',
                background: 'linear-gradient(135deg, rgba(0, 122, 255, 0.1) 0%, rgba(90, 200, 250, 0.1) 100%)',
                color: 'primary.main',
                fontWeight: 600,
                boxShadow: '0 4px 16px rgba(0, 122, 255, 0.2)',
                '&:hover': {
                  background: 'linear-gradient(135deg, rgba(0, 122, 255, 0.15) 0%, rgba(90, 200, 250, 0.15) 100%)',
                },
              },
            }
          }}
        >
          {conversationTypes.map((type) => (
            <ToggleButton key={type.value} value={type.value}>
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: { xs: 0.5, sm: 1 } }}>
                <Box sx={{ fontSize: { xs: 24, sm: 28 } }}>{type.icon}</Box>
                <Typography variant="body2" fontWeight="bold" sx={{ fontSize: { xs: '0.85rem', sm: '0.875rem' } }}>
                  {type.label}
                </Typography>
                <Typography 
                  variant="caption" 
                  color="text.secondary" 
                  textAlign="center" 
                  sx={{ 
                    lineHeight: 1.4,
                    fontSize: { xs: '0.7rem', sm: '0.75rem' },
                    display: { xs: 'none', sm: 'block' },
                  }}
                >
                  {type.description}
                </Typography>
              </Box>
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        {currentType && (
          <Fade in={true}>
            <Box 
              sx={{ 
                mt: 2, 
                p: 2, 
                borderRadius: 2.5,
                background: 'rgba(0, 122, 255, 0.05)',
                border: '1px solid rgba(0, 122, 255, 0.1)',
              }}
            >
              <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'primary.main' }}>
                ✓ Selected: {currentType.label}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {currentType.description}
              </Typography>
            </Box>
          </Fade>
        )}

        <Collapse in={showDetails}>
          <Box sx={{ mt: 2 }}>
            {currentRecommendation ? (
              <Alert 
                severity="info" 
                sx={{ 
                  mb: 2,
                  borderRadius: 2.5,
                  background: 'rgba(90, 200, 250, 0.1)',
                  border: '1px solid rgba(90, 200, 250, 0.3)',
                }}
              >
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                  💡 Recommended Strategy: {currentRecommendation.strategy}
                </Typography>
                <Typography variant="body2" gutterBottom>
                  {currentRecommendation.description}
                </Typography>
                
                {currentRecommendation.benefits && currentRecommendation.benefits.length > 0 && (
                  <Box sx={{ mt: 1.5 }}>
                    <Typography variant="caption" fontWeight="bold" sx={{ mb: 1, display: 'block' }}>
                      Benefits:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
                      {currentRecommendation.benefits.map((benefit: string, index: number) => (
                        <Chip 
                          key={index} 
                          label={benefit} 
                          size="small" 
                          variant="outlined"
                          sx={{
                            borderRadius: 1.5,
                            fontWeight: 500,
                            borderColor: 'info.main',
                            color: 'info.dark',
                          }}
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Alert>
            ) : loading ? (
              <Alert severity="info" className="loading-pulse" sx={{ borderRadius: 2.5 }}>Loading recommendations...</Alert>
            ) : null}

            <Box 
              sx={{ 
                p: 2, 
                borderRadius: 2.5,
                background: 'rgba(245, 245, 247, 0.5)',
              }}
            >
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                <strong style={{ color: '#34C759' }}>Quick Query:</strong> Best for simple, independent questions that don't require context from previous conversations.
                <br /><br />
                <strong style={{ color: '#007AFF' }}>Research:</strong> Ideal for exploratory research where you want to build upon previous findings and maintain research context.
                <br /><br />
                <strong style={{ color: '#5AC8FA' }}>Analysis:</strong> Perfect for deep paper analysis and literature reviews that require detailed context retention.
                <br /><br />
                <strong style={{ color: '#5856D6' }}>General:</strong> Balanced approach that adapts to conversation complexity automatically.
              </Typography>
            </Box>
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default ConversationTypeSelector;
