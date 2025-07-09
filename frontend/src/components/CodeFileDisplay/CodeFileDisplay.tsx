import React, { useState } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
  Paper,
  Divider,
  useTheme,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  Code as CodeIcon,
  InsertDriveFile as FileIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { FileContentInfo, CodeSnippet } from '../../types/api.types';

interface CodeFileDisplayProps {
  files: (FileContentInfo | string)[];
}

interface CodeSnippetDisplayProps {
  snippet: CodeSnippet;
  fileName: string;
  index: number;
}

const CodeSnippetDisplay: React.FC<CodeSnippetDisplayProps> = ({ snippet, fileName, index }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const [copied, setCopied] = useState(false);
  
  const handleCopyCode = async () => {
    try {
      await navigator.clipboard.writeText(snippet.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  };

  // Determine language from file extension
  const getLanguage = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    const languageMap: { [key: string]: string } = {
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'py': 'python',
      'c': 'c',
      'cs': 'csharp',
      'cpp': 'cpp',
      'cc': 'cpp',
      'cxx': 'cpp',
      'h': 'c',
      'hpp': 'cpp',
      'java': 'java',
      'php': 'php',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'sh': 'bash',
      'bash': 'bash',
      'zsh': 'bash',
      'fish': 'bash',
      'ps1': 'powershell',
      'sql': 'sql',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'less': 'less',
      'yaml': 'yaml',
      'yml': 'yaml',
      'toml': 'toml',
      'ini': 'ini',
      'cfg': 'ini',
      'conf': 'bash',
      'dockerfile': 'dockerfile',
      'md': 'markdown',
      'vert': 'glsl',
      'frag': 'glsl',
      'glsl': 'glsl',
      'cmake': 'cmake',
      'makefile': 'makefile',
    };
    return languageMap[ext || ''] || 'text';
  };

  const language = getLanguage(fileName);

  return (
    <Paper 
      variant="outlined" 
      sx={{ 
        mb: 2,
        overflow: 'hidden',
        '&:last-child': { mb: 0 }
      }}
    >
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        p: 1.5,
        bgcolor: 'action.hover'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CodeIcon fontSize="small" color="primary" />
          <Typography variant="body2" fontWeight="medium">
            Snippet {index + 1}: Lines {snippet.start_line}-{snippet.end_line}
          </Typography>
          <Chip 
            label={language.toUpperCase()} 
            size="small" 
            variant="outlined"
            sx={{ fontSize: '0.7rem', height: '20px' }}
          />
        </Box>
        <Tooltip title={copied ? "Copied!" : "Copy code"}>
          <IconButton 
            size="small" 
            onClick={handleCopyCode}
            sx={{
              transition: 'all 0.3s ease-in-out',
              '&:hover': {
                transform: 'scale(1.1)',
                backgroundColor: 'action.hover',
              }
            }}
          >
            <CopyIcon 
              fontSize="small" 
              sx={{ 
                color: copied ? 'success.main' : 'inherit',
                transition: 'color 0.3s ease-in-out'
              }} 
            />
          </IconButton>
        </Tooltip>
      </Box>
      
      <Box sx={{ 
        maxHeight: '400px', 
        overflow: 'auto',
        '& pre': { 
          margin: 0,
          fontSize: '0.875rem !important',
          lineHeight: '1.4 !important'
        }
      }}>
        <SyntaxHighlighter
          language={language}
          style={isDark ? oneDark : oneLight}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: 'transparent',
          }}
          showLineNumbers={false} // We already have line numbers in the content
          wrapLines={true}
          wrapLongLines={true}
        >
          {snippet.content}
        </SyntaxHighlighter>
      </Box>
    </Paper>
  );
};

const CodeFileDisplay: React.FC<CodeFileDisplayProps> = ({ files }) => {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  const handleFileToggle = (filePath: string, isExpanded: boolean) => {
    setExpandedFiles(prev => {
      const newSet = new Set(prev);
      if (isExpanded) {
        newSet.add(filePath);
      } else {
        newSet.delete(filePath);
      }
      return newSet;
    });
  };

  // Handle different data formats - should now be proper objects from fixed backend
  const normalizedFiles = React.useMemo(() => {
    if (!files || files.length === 0) return [];
    
    console.log('CodeFileDisplay received files:', files); // Debug logging
    
    return files
      .filter(file => file && typeof file === 'object' && 'file_path' in file)
      .map((file, index) => {
        console.log(`Processing file ${index}:`, typeof file, file); // Debug logging
        
        // TypeScript now knows file is FileContentInfo
        const fileInfo = file as FileContentInfo;
        return {
          file_path: fileInfo.file_path || 'Unknown file',
          snippets: fileInfo.snippets || [],
          size_kb: fileInfo.size_kb,
          relevance_score: fileInfo.relevance_score,
          selection_reason: fileInfo.selection_reason,
        } as FileContentInfo;
      });
  }, [files]);

  if (normalizedFiles.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 3 }}>
        <Typography variant="body2" color="text.secondary">
          No relevant code files found
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {normalizedFiles.map((file, fileIndex) => {
        const isExpanded = expandedFiles.has(file.file_path);
        const snippets = file.snippets || [];
        const hasSnippets = snippets.length > 0;

        return (
          <Accordion
            key={`${file.file_path}-${fileIndex}`}
            expanded={isExpanded}
            onChange={(_, expanded) => handleFileToggle(file.file_path, expanded)}
            TransitionProps={{ 
              timeout: 300
            }}
            sx={{ 
              mb: 1,
              '&:before': { display: 'none' },
              boxShadow: 1,
              '&.Mui-expanded': {
                margin: '0 0 8px 0',
              }
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                '& .MuiAccordionSummary-content': {
                  alignItems: 'center',
                  gap: 2,
                },
                '& .MuiAccordionSummary-content.Mui-expanded': {
                  margin: '12px 0',
                }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, minWidth: 0, flex: 1 }}>
                <FileIcon color="primary" />
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography 
                    variant="subtitle1" 
                    fontWeight="medium"
                    sx={{ 
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {file.file_path}
                  </Typography>
                  {file.size_kb && (
                    <Typography variant="caption" color="text.secondary">
                      {file.size_kb.toFixed(1)} KB
                    </Typography>
                  )}
                </Box>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexShrink: 0 }}>
                  {hasSnippets && (
                    <Chip
                      label={`${snippets.length} snippet${snippets.length !== 1 ? 's' : ''}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{
                        transition: 'all 0.3s ease-in-out',
                        '&:hover': {
                          transform: 'scale(1.05)',
                          boxShadow: 1,
                        }
                      }}
                    />
                  )}
                  {file.relevance_score && (
                    <Chip
                      label={`${Math.round(file.relevance_score * 100)}% relevant`}
                      size="small"
                      color="secondary"
                      variant="outlined"
                      sx={{
                        transition: 'all 0.3s ease-in-out',
                        '&:hover': {
                          transform: 'scale(1.05)',
                          boxShadow: 1,
                        }
                      }}
                    />
                  )}
                </Box>
              </Box>
            </AccordionSummary>
            
            <AccordionDetails sx={{ pt: 0 }}>
              {file.selection_reason && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    Selected because: {file.selection_reason}
                  </Typography>
                  <Divider sx={{ mt: 1, mb: 2 }} />
                </Box>
              )}

              {hasSnippets ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {snippets.length} relevant code snippet{snippets.length !== 1 ? 's' : ''} found:
                  </Typography>
                  {snippets.map((snippet, snippetIndex) => (
                    <CodeSnippetDisplay
                      key={`${file.file_path}-snippet-${snippetIndex}`}
                      snippet={snippet}
                      fileName={file.file_path}
                      index={snippetIndex}
                    />
                  ))}
                </Box>
              ) : (
                <Box sx={{ textAlign: 'center', py: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    No code snippets available for this file
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    This file was identified as relevant but no specific code snippets were extracted.
                  </Typography>
                </Box>
              )}
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Box>
  );
};

export default CodeFileDisplay;
