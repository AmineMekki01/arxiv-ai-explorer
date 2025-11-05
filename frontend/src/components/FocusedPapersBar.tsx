import React from 'react';
import { Box, Alert, Chip, Button, Stack, Typography, Collapse } from '@mui/material';
import { PushPin as PushPinIcon } from '@mui/icons-material';

interface FocusedPaper {
  arxiv_id: string;
  title: string;
  citations?: number;
}

interface FocusedPapersBarProps {
  focusedPapers: FocusedPaper[];
  onRemove: (arxivId: string) => void;
  onClearAll: () => void;
}

export const FocusedPapersBar: React.FC<FocusedPapersBarProps> = ({
  focusedPapers,
  onRemove,
  onClearAll
}) => {
  if (focusedPapers.length === 0) return null;

  return (
    <Collapse in={focusedPapers.length > 0}>
      <Alert 
        severity="info" 
        sx={{ 
          mb: 2,
          bgcolor: 'primary.50',
          border: '2px solid',
          borderColor: 'primary.main',
          borderRadius: 2,
          '& .MuiAlert-icon': {
            color: 'primary.main'
          }
        }}
        icon={<PushPinIcon />}
        action={
          <Button 
            size="small" 
            onClick={onClearAll}
            sx={{ 
              color: 'primary.main',
              fontWeight: 600,
              '&:hover': {
                bgcolor: 'primary.100'
              }
            }}
          >
            Clear All
          </Button>
        }
      >
        <Box>
          <Typography variant="body2" fontWeight="bold" sx={{ mb: 0.5 }}>
            📌 Focused Mode ({focusedPapers.length} paper{focusedPapers.length !== 1 ? 's' : ''})
          </Typography>
          <Typography variant="caption" display="block" sx={{ mb: 1.5, color: 'text.secondary' }}>
            💡 Your questions will prioritize these papers for more focused answers
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ gap: 1 }}>
            {focusedPapers.map(paper => (
              <Chip
                key={paper.arxiv_id}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Typography variant="caption" sx={{ fontWeight: 600 }}>
                      {paper.title.length > 50 ? paper.title.substring(0, 50) + '...' : paper.title}
                    </Typography>
                    {paper.citations && (
                      <Typography variant="caption" sx={{ opacity: 0.7, fontSize: '0.65rem' }}>
                        ({paper.citations.toLocaleString()} citations)
                      </Typography>
                    )}
                  </Box>
                }
                onDelete={() => onRemove(paper.arxiv_id)}
                color="primary"
                size="small"
                sx={{
                  height: 'auto',
                  py: 0.75,
                  '& .MuiChip-label': {
                    px: 1.5,
                    py: 0.5
                  }
                }}
              />
            ))}
          </Stack>
        </Box>
      </Alert>
    </Collapse>
  );
};
