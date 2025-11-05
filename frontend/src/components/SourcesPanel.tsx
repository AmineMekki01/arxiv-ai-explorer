import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  Tooltip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  OpenInNew as OpenInNewIcon,
  PushPin as PushPinIcon,
  PushPinOutlined as PushPinOutlinedIcon,
} from '@mui/icons-material';

interface ChunkDetail {
  section: string;
  text_preview: string;
  score: number;
}

interface Source {
  arxiv_id: string;
  title: string;
  chunks_used: number;
  citation_count: number;
  is_seminal: boolean;
  is_foundational: boolean;
  cited_by_results: number;
  chunk_details?: ChunkDetail[];
}

interface SourcesPanelProps {
  sources: Source[];
  focusedPapers: string[];
  onFocus: (arxivId: string, title: string) => void;
  onUnfocus: (arxivId: string) => void;
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({
  sources,
  focusedPapers,
  onFocus,
  onUnfocus
}) => {
  if (!sources || sources.length === 0) return null;

  const totalChunks = sources.reduce((sum, s) => sum + s.chunks_used, 0);

  return (
    <Paper 
      elevation={0}
      sx={{ 
        mt: 2, 
        p: 2, 
        bgcolor: 'grey.50',
        border: '1px solid',
        borderColor: 'grey.200',
        borderRadius: 2,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
        <Typography variant="subtitle2" fontWeight="bold" sx={{ flex: 1 }}>
          📚 Sources ({sources.length} paper{sources.length !== 1 ? 's' : ''}, {totalChunks} chunk{totalChunks !== 1 ? 's' : ''})
        </Typography>
      </Box>

      <Stack spacing={1}>
        {sources.map((source, idx) => {
          const isFocused = focusedPapers.includes(source.arxiv_id);
          
          return (
            <Accordion 
              key={source.arxiv_id}
              disableGutters
              elevation={0}
              sx={{
                bgcolor: isFocused ? 'primary.50' : 'white',
                border: '1px solid',
                borderColor: isFocused ? 'primary.main' : 'grey.300',
                '&:before': { display: 'none' },
                borderRadius: '8px !important',
                '&:first-of-type': { borderRadius: '8px !important' },
                '&:last-of-type': { borderRadius: '8px !important' },
              }}
            >
              <AccordionSummary 
                expandIcon={<ExpandMoreIcon />}
                sx={{ 
                  px: 2,
                  '& .MuiAccordionSummary-content': { my: 1.5 }
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', pr: 1 }}>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    {/* Title */}
                    <Typography 
                      variant="body2" 
                      fontWeight="bold" 
                      sx={{ mb: 0.5 }}
                      noWrap
                    >
                      [{idx + 1}] {source.title}
                    </Typography>
                    
                    {/* Badges */}
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ gap: 0.5 }}>
                      {source.is_seminal && (
                        <Tooltip title={`${source.citation_count.toLocaleString()} citations`}>
                          <Chip 
                            label="⭐ Seminal" 
                            size="small" 
                            sx={{ 
                              bgcolor: 'warning.100',
                              color: 'warning.900',
                              fontWeight: 600,
                              fontSize: '0.7rem'
                            }}
                          />
                        </Tooltip>
                      )}
                      {source.is_foundational && (
                        <Tooltip title={`Cited by ${source.cited_by_results} papers in results`}>
                          <Chip 
                            label="🏛️ Foundational" 
                            size="small" 
                            sx={{ 
                              bgcolor: 'secondary.100',
                              color: 'secondary.900',
                              fontWeight: 600,
                              fontSize: '0.7rem'
                            }}
                          />
                        </Tooltip>
                      )}
                      {source.cited_by_results > 0 && !source.is_foundational && (
                        <Tooltip title={`Central to ${source.cited_by_results} results`}>
                          <Chip 
                            label="📊 Central" 
                            size="small" 
                            sx={{ 
                              bgcolor: 'info.100',
                              color: 'info.900',
                              fontWeight: 600,
                              fontSize: '0.7rem'
                            }}
                          />
                        </Tooltip>
                      )}
                      <Chip 
                        label={`${source.chunks_used} chunk${source.chunks_used !== 1 ? 's' : ''}`}
                        size="small" 
                        variant="outlined"
                        sx={{ fontSize: '0.7rem' }}
                      />
                      {!source.is_seminal && (
                        <Chip 
                          label={`${source.citation_count.toLocaleString()} citations`}
                          size="small" 
                          variant="outlined"
                          sx={{ fontSize: '0.7rem' }}
                        />
                      )}
                    </Stack>
                  </Box>
                  
                  {/* Action buttons */}
                  <Stack direction="row" spacing={0.5} onClick={(e) => e.stopPropagation()}>
                    <Tooltip title={isFocused ? "Unfocus - return to general search" : "Focus on this paper only"}>
                      <IconButton
                        size="small"
                        onClick={() => isFocused ? onUnfocus(source.arxiv_id) : onFocus(source.arxiv_id, source.title)}
                        sx={{ 
                          color: isFocused ? 'primary.main' : 'text.secondary',
                          '&:hover': {
                            bgcolor: isFocused ? 'primary.50' : 'grey.100'
                          }
                        }}
                      >
                        {isFocused ? <PushPinIcon fontSize="small" /> : <PushPinOutlinedIcon fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Open in arXiv">
                      <IconButton
                        size="small"
                        component="a"
                        href={`https://arxiv.org/abs/${source.arxiv_id.replace('v', '')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ color: 'text.secondary' }}
                      >
                        <OpenInNewIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              </AccordionSummary>
              
              {/* Chunk details */}
              {source.chunk_details && source.chunk_details.length > 0 && (
                <AccordionDetails sx={{ pt: 0, px: 2, pb: 2 }}>
                  <Divider sx={{ mb: 1.5 }} />
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                    Relevant sections used:
                  </Typography>
                  <Stack spacing={1}>
                    {source.chunk_details.map((chunk, chunkIdx) => (
                      <Paper key={chunkIdx} elevation={0} sx={{ p: 1.5, bgcolor: 'grey.100', border: '1px solid', borderColor: 'grey.200' }}>
                        <Typography variant="caption" color="primary" fontWeight="bold" sx={{ display: 'block', mb: 0.5 }}>
                          {chunk.section || 'Section'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', lineHeight: 1.4 }}>
                          {chunk.text_preview}...
                        </Typography>
                        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.5, display: 'block' }}>
                          Relevance: {chunk.score.toFixed(3)}
                        </Typography>
                      </Paper>
                    ))}
                  </Stack>
                </AccordionDetails>
              )}
            </Accordion>
          );
        })}
      </Stack>
    </Paper>
  );
};
