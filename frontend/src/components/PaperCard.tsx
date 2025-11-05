import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Button,
  Stack,
  Paper,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Article as ArticleIcon,
  CalendarToday as CalendarIcon,
  Category as CategoryIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';
import { PaperResult } from '../types/search';

interface PaperCardProps {
  paper: PaperResult;
  onViewDetails?: (arxivId: string) => void;
}

export const PaperCard: React.FC<PaperCardProps> = ({ paper, onViewDetails }) => {
  const { arxiv_id, title, published_date, primary_category, categories, chunks, graph_metadata } = paper;

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getBadges = (): Array<{ label: string; color: 'secondary' | 'warning' | 'info'; tooltip: string }> => {
    const badges: Array<{ label: string; color: 'secondary' | 'warning' | 'info'; tooltip: string }> = [];
    
    if (graph_metadata.is_foundational) {
      badges.push({ 
        label: '🏛️ Foundational', 
        color: 'secondary', 
        tooltip: `Cited by ${graph_metadata.cited_by_results} papers in these results` 
      });
    }
    
    if (graph_metadata.is_seminal) {
      badges.push({ 
        label: '⭐ Seminal', 
        color: 'warning', 
        tooltip: `${graph_metadata.citation_count} citations` 
      });
    }
    
    if (graph_metadata.cited_by_results > 0 && !graph_metadata.is_foundational) {
      badges.push({ 
        label: `📊 Central`, 
        color: 'info', 
        tooltip: `Cited by ${graph_metadata.cited_by_results} other results` 
      });
    }
    
    return badges;
  };

  const badges = getBadges();

  return (
    <Card elevation={2} sx={{ '&:hover': { boxShadow: 4 }, transition: 'box-shadow 0.2s' }}>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ flex: 1, pr: 2 }}>
            <Typography 
              variant="h6" 
              component="h3" 
              gutterBottom
              sx={{ 
                cursor: 'pointer',
                '&:hover': { color: 'primary.main' },
                fontWeight: 600 
              }}
              onClick={() => onViewDetails?.(arxiv_id)}
            >
              {title}
            </Typography>
            
            {/* Badges */}
            {badges.length > 0 && (
              <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap', gap: 1 }}>
                {badges.map((badge, idx) => (
                  <Tooltip key={idx} title={badge.tooltip} arrow>
                    <Chip 
                      label={badge.label}
                      size="small"
                      color={badge.color}
                    />
                  </Tooltip>
                ))}
              </Stack>
            )}
          </Box>
          
          {/* Citation count */}
          <Box sx={{ textAlign: 'center', minWidth: 80 }}>
            <Typography variant="caption" color="text.secondary">
              Citations
            </Typography>
            <Typography variant="h5" fontWeight="bold">
              {graph_metadata.citation_count.toLocaleString()}
            </Typography>
          </Box>
        </Box>

        {/* Metadata Row */}
        <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CalendarIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {formatDate(published_date)}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CategoryIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {primary_category || 'N/A'}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <ArticleIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {chunks.length} relevant section{chunks.length !== 1 ? 's' : ''}
            </Typography>
          </Box>
        </Stack>

        {/* Top chunk preview */}
        {chunks.length > 0 && (
          <Paper 
            elevation={0} 
            sx={{ 
              p: 2, 
              mb: 2, 
              bgcolor: 'grey.50',
              border: '1px solid',
              borderColor: 'grey.200'
            }}
          >
            <Typography variant="caption" color="primary" fontWeight="bold" gutterBottom display="block">
              {chunks[0].section_title || 'Relevant Section'}
            </Typography>
            <Typography 
              variant="body2" 
              color="text.secondary"
              sx={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {chunks[0].chunk_text}
            </Typography>
          </Paper>
        )}

        {/* Actions */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pt: 1 }}>
          <Stack direction="row" spacing={1}>
            <Button 
              variant="contained"
              size="small"
              onClick={() => onViewDetails?.(arxiv_id)}
            >
              View Details
            </Button>
            <Button
              variant="outlined"
              size="small"
              endIcon={<OpenInNewIcon fontSize="small" />}
              href={`https://arxiv.org/abs/${arxiv_id.replace('v', '')}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              arXiv
            </Button>
          </Stack>
          
          {/* Categories pills */}
          <Stack direction="row" spacing={0.5}>
            {categories.slice(0, 3).map((cat) => (
              <Chip 
                key={cat}
                label={cat}
                size="small"
                variant="outlined"
              />
            ))}
            {categories.length > 3 && (
              <Chip 
                label={`+${categories.length - 3}`}
                size="small"
                variant="outlined"
              />
            )}
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};
