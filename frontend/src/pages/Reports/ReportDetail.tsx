import React, { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Button,
  Chip,
  LinearProgress,
  Divider,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  Snackbar,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Print as PrintIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Schedule as TimeIcon,
  Code as CodeIcon,
  Assignment as AssignmentIcon,
  BugReport as BugReportIcon,
  Assessment as AssessmentIcon,
  AccountTree as GitIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  CheckBox as CheckBoxIcon,
  CheckBoxOutlineBlank as CheckBoxOutlineBlankIcon,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { useReport, useDownloadMarkdown, useDeleteReport } from '../../hooks/useApi';
import ReactMarkdown from 'react-markdown';
import CodeFileDisplay from '../../components/CodeFileDisplay';
import { DeleteConfirmationDialog } from '../../components/Common/DeleteConfirmationDialog';

export const ReportDetail: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  const { data: report, isLoading, error } = useReport(reportId || '');
  const downloadMarkdown = useDownloadMarkdown();
  const deleteReport = useDeleteReport();
  const title = report?.title || 'Report Title Not Available';

  // Delete confirmation dialog state
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    reportId: string;
    reportName: string;
  }>({
    open: false,
    reportId: '',
    reportName: '',
  });

  // Success/error feedback state
  const [feedback, setFeedback] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const handleDownloadReport = async () => {
    if (reportId) {
      try {
        await downloadMarkdown.mutateAsync(reportId);
      } catch (error) {
        console.error('Failed to download report:', error);
      }
    }
  };

  const handleDeleteClick = () => {
    if (reportId && report) {
      setDeleteDialog({
        open: true,
        reportId,
        reportName: title,
      });
    }
  };

  const handleDeleteConfirm = async () => {
    try {
      await deleteReport.mutateAsync(deleteDialog.reportId);
      setFeedback({
        open: true,
        message: 'Report deleted successfully',
        severity: 'success',
      });
      setDeleteDialog({ open: false, reportId: '', reportName: '' });
      // Navigate back to reports list after successful deletion
      setTimeout(() => {
        navigate('/reports');
      }, 1500);
    } catch (error) {
      setFeedback({
        open: true,
        message: 'Failed to delete report',
        severity: 'error',
      });
      console.error('Failed to delete report:', error);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialog({ open: false, reportId: '', reportName: '' });
  };

  const handleFeedbackClose = () => {
    setFeedback({ open: false, message: '', severity: 'success' });
  };

  if (!reportId) {
    return (
      <Alert severity="error">
        No report ID provided
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/reports')}
          sx={{ mb: 2 }}
        >
          Back to Reports
        </Button>
        <Alert severity="error">
          Failed to load report: {error.message}
        </Alert>
      </Box>
    );
  }

  if (!report) {
    return (
      <Box>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/reports')}
          sx={{ mb: 2 }}
        >
          Back to Reports
        </Button>
        <Alert severity="warning">
          Report not found
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with navigation and actions */}
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        mb: 3,
        flexWrap: 'wrap',
        gap: 2
      }}>
        <Box>
          <Button
            startIcon={<BackIcon />}
            onClick={() => navigate('/reports')}
            sx={{ mb: 1 }}
          >
            Back to Reports
          </Button>
          <Typography variant="h4" component="h1">
            {title}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 2 }}>
            {report.confidence_score !== undefined && (
              <Chip
                label={`Confidence: ${Math.round(report.confidence_score * 100)}%`}
                size="small"
                variant="outlined"
                color={
                  report.confidence_score >= 0.8
                    ? 'success'
                    : report.confidence_score >= 0.6
                    ? 'warning'
                    : 'error'
                }
              />
            )}
            {report.error_type && (
              <Chip
                label={`${report.error_type}`}
                color="error"
                variant="outlined"
                size="small"
              />
            )}
            {report.diagnosis_id && (
              <Chip
                label={`${report.diagnosis_id}`}
                size="small"
                variant="outlined"
              />
            )}
            {report.relevant_code_files && (
              <Chip
                label={`${report.relevant_code_files.length} Files Analyzed`}
                size="small"
                variant="outlined"
              />
            )}
            {report.created && (
            <Chip
                icon={<TimeIcon />}
                label={`Timestamp: ${new Date(report.created).toLocaleString()}`}
                size="small"
                variant="outlined"
            />
            )}
            {report.processing_time !== undefined && (
            <Chip
                icon={<TimeIcon />}
                label={`Processing Time: ${report.processing_time.toFixed(1)}s`}
                size="small"
                variant="outlined"
            />
            )}
            {report.timestamp && (
            <Chip
                icon={<TimeIcon />}
                label={`Timestamp: ${new Date(report.timestamp).toLocaleString()}`}
                size="small"
                variant="outlined"
            />
            )}
          </Box>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadReport}
            disabled={downloadMarkdown.isPending}
          >
            {downloadMarkdown.isPending ? 'Downloading...' : 'Download'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<PrintIcon />}
            onClick={() => window.print()}
          >
            Print
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleDeleteClick}
            disabled={deleteReport.isPending}
          >
            Delete
          </Button>
        </Box>
      </Box>

      {/* Report Content */}
      <Card>
        <CardContent>
          <Box sx={{ 
            '& h1, & h2, & h3, & h4, & h5, & h6': {
              color: 'primary.main',
              mt: 3,
              mb: 2,
              '&:first-of-type': { mt: 0 }
            },
            '& p': {
              mb: 2,
              lineHeight: 1.6
            },
            '& ul, & ol': {
              mb: 2,
              pl: 3
            },
            '& li': {
              mb: 0.5
            },
            '& pre': {
              backgroundColor: 'grey.100',
              p: 2,
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.875rem'
            },
            '& code': {
              backgroundColor: 'grey.100',
              px: 0.5,
              py: 0.25,
              borderRadius: 0.5,
              fontSize: '0.875rem'
            },
            '& blockquote': {
              borderLeft: '4px solid',
              borderColor: 'primary.main',
              pl: 2,
              ml: 0,
              fontStyle: 'italic',
              color: 'text.secondary'
            }
          }}>
            {/* Display structured content if available, otherwise show full markdown */}
            {report.root_cause || report.error_analysis || (report.recommendations && report.recommendations.length > 0) ? (
              <>
                {/* Summary */}
                {report.summary && (
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h5" component="h2" gutterBottom>
                      Summary
                    </Typography>
                    <ReactMarkdown>{report.summary}</ReactMarkdown>
                  </Box>
                )}

                {/* Root Cause */}
                {report.root_cause && (
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h5" component="h2" gutterBottom>
                      Root Cause Analysis
                    </Typography>
                    <ReactMarkdown>{report.root_cause}</ReactMarkdown>
                  </Box>
                )}

                {/* Error Analysis */}
                {report.error_analysis && (
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h5" component="h2" gutterBottom>
                      Error Analysis
                    </Typography>
                    <ReactMarkdown>{report.error_analysis}</ReactMarkdown>
                  </Box>
                )}

                {/* Recommendations */}
                {report.recommendations && report.recommendations.length > 0 && (
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h5" component="h2" gutterBottom>
                      Recommendations
                    </Typography>
                    <Box component="ol" sx={{ pl: 2 }}>
                      {report.recommendations.map((recommendation, index) => (
                        <Box component="li" key={index} sx={{ mb: 2 }}>
                          <ReactMarkdown>{recommendation}</ReactMarkdown>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                )}

                {/* Relevant Code Files */}
                {report.relevant_code_files && report.relevant_code_files.length > 0 && (
                  <Box sx={{ mb: 4 }}>
                    <Typography variant="h5" component="h2" gutterBottom>
                      Relevant Code Files
                    </Typography>
                    <CodeFileDisplay files={report.relevant_code_files as any} />
                  </Box>
                )}
              </>
            ) : (
              /* Fallback to full markdown content */
              report.summary && <ReactMarkdown>{report.summary}</ReactMarkdown>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        open={deleteDialog.open}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Report"
        itemName={deleteDialog.reportName}
        itemId={deleteDialog.reportId}
        isDeleting={deleteReport.isPending}
      />

      {/* Success/Error Feedback */}
      <Snackbar
        open={feedback.open}
        autoHideDuration={6000}
        onClose={handleFeedbackClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleFeedbackClose}
          severity={feedback.severity}
          sx={{ width: '100%' }}
        >
          {feedback.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};
