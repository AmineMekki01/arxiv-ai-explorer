import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
  Chip,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  Stack,
  Tooltip,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  Star as StarIcon,
  AccountBalance as FoundationIcon,
  TrendingUp as CentralIcon,
  PushPin as PinIcon,
  Link as LinkIcon,
  Info as InfoIcon,
  Favorite as FavoriteIcon,
} from '@mui/icons-material';
import { apiEndpoints } from '../services/api';

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
  chunk_details: ChunkDetail[];
}

interface SourcesSidebarProps {
  open: boolean;
  onClose: () => void;
  sources: Source[];
  onFocusPaper?: (arxivId: string, title: string) => void;
  focusedPapers?: Array<{ arxiv_id: string }>;
}

export const SourcesSidebar: React.FC<SourcesSidebarProps> = ({
  open,
  onClose,
  sources,
  onFocusPaper,
  focusedPapers = [],
}) => {
  const navigate = useNavigate();
  const totalChunks = sources.reduce((sum, s) => sum + s.chunks_used, 0);
  const isFocused = (arxivId: string) =>
    focusedPapers.some((p) => p.arxiv_id === arxivId);

  const [savedPaper, setSavedPaper] = useState<Set<string>>(new Set());
  const [snack, setSnack] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>(
    { open: false, message: '', severity: 'success' }
  );

  useEffect(() => {
    (async () => {
      try {
        const ids = new Set<string>();
        const res = await apiEndpoints.listSavedPapers();
        if (res.status === 200) {
          ids.add((res.data || []).map((b: any) => b.arxiv_id));
          console.log(ids);
          setSavedPaper(ids);
        }
      } catch {}
    })();
  }, []);

  const handleTogglePaperSave = async (arxivId: string, title: string) => {
    try {
      if (savedPaper.has(arxivId)) {
        const res = await apiEndpoints.unsavePaper(arxivId);
        if (res.status === 200) {
          setSavedPaper((prev) => {
            const next = new Set(prev);
            next.delete(arxivId);
            return next;
          });
          setSnack({ open: true, message: 'Removed from saved papers', severity: 'success' });
        }
      } else {
        const res = await apiEndpoints.savePaper(arxivId, title);
        if (res.status === 200) {
          setSavedPaper((prev) => new Set(prev).add(arxivId));
          setSnack({ open: true, message: 'Saved to saved papers', severity: 'success' });
        }
      }
    } catch {
      setSnack({ open: true, message: 'Save action failed', severity: 'error' });
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: 500 },
          maxWidth: '100vw',
        },
      }}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box
          sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: 1,
            borderColor: 'divider',
            bgcolor: 'primary.main',
            color: 'white',
          }}
        >
          <Box>
            <Typography variant="h6" fontWeight="bold">
              📚 Sources
            </Typography>
            <Typography variant="caption">
              {sources.length} papers · {totalChunks} chunks
            </Typography>
          </Box>
          <IconButton onClick={onClose} sx={{ color: 'white' }}>
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Sources List */}
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
          {sources.length === 0 ? (
            <Box
              sx={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography color="text.secondary">
                No sources available for this message
              </Typography>
            </Box>
          ) : (
            <Stack spacing={2}>
              {sources.map((source, index) => {
                const focused = isFocused(source.arxiv_id);
                return (
                  <Paper
                    key={source.arxiv_id}
                    elevation={focused ? 8 : 2}
                    sx={{
                      p: 2,
                      bgcolor: focused ? 'primary.50' : 'background.paper',
                      border: focused ? 2 : 1,
                      borderColor: focused ? 'primary.main' : 'divider',
                      transition: 'all 0.2s',
                    }}
                  >
                    {/* Paper Header */}
                    <Box sx={{ mb: 1 }}>
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        sx={{ mb: 0.5 }}
                      >
                        [{index + 1}]
                      </Typography>
                      <Typography variant="h6" sx={{ mb: 1, lineHeight: 1.3 }}>
                        {source.title}
                      </Typography>

                      {/* Badges */}
                      <Stack direction="row" spacing={1} sx={{ mb: 1.5 }} flexWrap="wrap">
                        {source.is_seminal && (
                          <Tooltip title={`${source.citation_count.toLocaleString()} citations`}>
                            <Chip
                              icon={<StarIcon />}
                              label="Seminal"
                              size="small"
                              color="warning"
                              sx={{ fontWeight: 'bold' }}
                            />
                          </Tooltip>
                        )}
                        {source.is_foundational && (
                          <Tooltip title="Discovered by graph analysis">
                            <Chip
                              icon={<FoundationIcon />}
                              label="Foundational"
                              size="small"
                              color="info"
                            />
                          </Tooltip>
                        )}
                        {source.cited_by_results > 0 && (
                          <Tooltip title={`Cited by ${source.cited_by_results} papers in results`}>
                            <Chip
                              icon={<CentralIcon />}
                              label="Central"
                              size="small"
                              color="success"
                            />
                          </Tooltip>
                        )}
                      </Stack>

                      {/* Metadata */}
                      <Box sx={{ display: 'flex', gap: 2, mb: 1.5 }}>
                        <Typography variant="body2" color="text.secondary">
                          {source.chunks_used} chunk{source.chunks_used !== 1 ? 's' : ''}
                        </Typography>
                        {source.citation_count > 0 && (
                          <Typography variant="body2" color="text.secondary">
                            {source.citation_count.toLocaleString()} citations
                          </Typography>
                        )}
                      </Box>
                    </Box>

                    {/* Chunks Accordion */}
                    {source.chunk_details && source.chunk_details.length > 0 && (
                      <Accordion
                        elevation={0}
                        sx={{ bgcolor: 'transparent', '&:before': { display: 'none' } }}
                      >
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="body2" fontWeight="medium">
                            View {source.chunk_details.length} chunk
                            {source.chunk_details.length !== 1 ? 's' : ''}
                          </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <Stack spacing={1.5}>
                            {source.chunk_details.map((chunk, idx) => (
                              <Paper
                                key={idx}
                                variant="outlined"
                                sx={{ p: 1.5, bgcolor: 'grey.50' }}
                              >
                                <Typography
                                  variant="caption"
                                  color="primary"
                                  fontWeight="bold"
                                  sx={{ display: 'block', mb: 0.5 }}
                                >
                                  {chunk.section}
                                </Typography>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    mb: 0.5,
                                    fontStyle: 'italic',
                                    color: 'text.secondary',
                                  }}
                                >
                                  "{chunk.text_preview}..."
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  Relevance: {(chunk.score * 100).toFixed(1)}%
                                </Typography>
                              </Paper>
                            ))}
                          </Stack>
                        </AccordionDetails>
                      </Accordion>
                    )}

                    {/* Actions */}
                    <Divider sx={{ my: 1.5 }} />
                    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<InfoIcon />}
                        onClick={() => navigate(`/paper/${source.arxiv_id}`)}
                      >
                        View Details
                      </Button>
                      <Button
                        size="small"
                        variant={savedPaper.has(source.arxiv_id) ? 'contained' : 'outlined'}
                        color={savedPaper.has(source.arxiv_id) ? 'secondary' : 'primary'}
                        startIcon={<FavoriteIcon />}
                        onClick={() => handleTogglePaperSave(source.arxiv_id, source.title)}
                      >
                        {savedPaper.has(source.arxiv_id) ? 'Saved' : 'Save'}
                      </Button>
                      {onFocusPaper && (
                        <Button
                          size="small"
                          variant={focused ? 'contained' : 'outlined'}
                          startIcon={<PinIcon />}
                          onClick={() => onFocusPaper(source.arxiv_id, source.title)}
                        >
                          {focused ? 'Focused' : 'Focus'}
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<LinkIcon />}
                        href={`https://arxiv.org/abs/${source.arxiv_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        arXiv
                      </Button>
                    </Stack>
                  </Paper>
                );
              })}
            </Stack>
          )}
        </Box>
      </Box>
      <Snackbar
        open={snack.open}
        autoHideDuration={2500}
        onClose={() => setSnack((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSnack((s) => ({ ...s, open: false }))} severity={snack.severity} sx={{ width: '100%' }}>
          {snack.message}
        </Alert>
      </Snackbar>
    </Drawer>
  );
};
