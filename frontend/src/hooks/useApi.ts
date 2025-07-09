import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportsApi, systemApi } from '../services/api';
import type {
  DiagnosisResult,
  HealthStatus,
  SystemStats,
  ReportsListResponse,
} from '../types/api.types';

// Query Keys
export const queryKeys = {
  reports: ['reports'] as const,
  report: (reportId: string) => ['reports', reportId] as const,
  health: ['health'] as const,
  stats: ['stats'] as const,
};

// Reports Hooks
export const useReports = () => {
  return useQuery({
    queryKey: queryKeys.reports,
    queryFn: async () => {
      const response = await reportsApi.getReports();
      const reportsResponse = response.data as ReportsListResponse;
      return reportsResponse.reports;
    },
  });
};

export const useReport = (reportId: string) => {
  return useQuery({
    queryKey: queryKeys.report(reportId),
    queryFn: async () => {
      const response = await reportsApi.getReport(reportId);
      // The backend now returns the JSON report directly
      const jsonReport = response.data;
      
      // Debug logging
      console.log('JSON Report data received:', jsonReport);
      
      // Extract data from JSON structure
      const metadata = jsonReport.metadata || {};
      const diagnosisResult = jsonReport.diagnosis_result || {};
      
      return {
        report_id: jsonReport.report_id,
        summary: diagnosisResult.summary || 'No summary available',
        title: diagnosisResult.title || 'Report Title Not Available',
        error_type: diagnosisResult.error_type || 'Unknown Error',
        root_cause: diagnosisResult.root_cause || '',
        error_analysis: diagnosisResult.error_analysis || '',
        recommendations: diagnosisResult.recommendations || [],
        confidence_score: diagnosisResult.confidence_score || 0,
        processing_time: metadata.processing_time_seconds || 0,
        relevant_code_files: diagnosisResult.relevant_code_files || [],
        timestamp: metadata.timestamp || '',
        diagnosis_id: metadata.diagnosis_id || '',
        git_info: jsonReport.git_info || {},
        parsed_log: jsonReport.parsed_log || {}
      } as DiagnosisResult & {
        report_id: string;
        error_type: string;
        diagnosis_id: string;
        git_info: any;
        parsed_log: any;
      };
    },
    enabled: !!reportId,
  });
};

export const useDeleteReport = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reportId: string) => {
      const response = await reportsApi.deleteReport(reportId);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate reports list to refresh after deletion
      queryClient.invalidateQueries({ queryKey: queryKeys.reports });
    },
  });
};

export const useDownloadMarkdown = () => {
  return useMutation({
    mutationFn: async (reportId: string) => {
      const response = await reportsApi.downloadMarkdown(reportId);
      
      // Create download link
      const blob = new Blob([response.data], { type: 'text/markdown' });
      const url = window.URL.createObjectURL(blob);
      
      // Extract filename from response headers or generate one
      const contentDisposition = response.headers['content-disposition'];
      let filename = `report_${reportId.slice(0, 8)}.md`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return { success: true, filename };
    },
  });
};

// System Hooks
export const useHealth = (refetchInterval?: number) => {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: async () => {
      const response = await systemApi.getHealth();
      return response.data as HealthStatus;
    },
    refetchInterval: refetchInterval || 30000, // Default 30 seconds
  });
};

export const useStats = () => {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: async () => {
      const response = await systemApi.getStats();
      return response.data as SystemStats;
    },
  });
};
