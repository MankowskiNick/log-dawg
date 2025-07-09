// API Response Types
export interface ApiResponse<T = unknown> {
  data: T;
  message?: string;
  status: string;
}

// Report Types
export interface ReportSummary {
  report_id: string;
  filename: string;
  created: string;
  size_bytes: number;
  diagnosis_id?: string;
  display_title?: string;
  error_type?: string;
  confidence_score?: number;
  processing_time?: number;
  summary_preview?: string;
  modified: string;
}

export interface DiagnosisResult {
  summary: string;
  root_cause: string;
  error_analysis: string;
  recommendations: string[];
  confidence_score: number;
  relevant_code_files?: FileContentInfo[];
  display_title?: string;
  error_type?: string;
  processing_time?: number;
  diagnosis_id?: string;
  title?: string;
  created?: string;
  timestamp?: string;
}

export interface CodeSnippet {
  start_line: number;
  end_line: number;
  content: string;
}

export interface FileContentInfo {
  file_path: string;
  content?: string | null;
  size_kb?: number;
  relevance_score?: number;
  selection_reason?: string;
  snippets?: CodeSnippet[];
}

// Git Information Types
export interface GitCommit {
  hash: string;
  message: string;
  author: string;
  date: string;
}

export interface GitInfo {
  current_commit: string;
  branch: string;
  recent_commits: GitCommit[];
  changed_files: string[];
  last_pull_time: string;
}

// System Health Types
export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  checks: {
    [key: string]: {
      status: 'pass' | 'fail' | 'warn';
      message?: string;
    };
  };
}

// Statistics Types
export interface ReportStats {
  total_reports: number;
  reports_today: number;
  average_confidence_score: number;
  processing_time_avg: number;
  last_analysis: string;
}

export interface GitStats {
  branch: string;
  current_commit: string;
  last_pull_time: string;
  recent_commits_count: number;
  changed_files_count: number;
}

export interface ConfigurationStats {
  valid: boolean;
  errors_count: number;
  warnings_count: number;
}

export interface SystemStats {
  reports: ReportStats;
  git: GitStats;
  configuration: ConfigurationStats;
  version: string;
  timestamp: string;
}

// Reports List Response
export interface ReportsListResponse {
  reports: ReportSummary[];
  stats: ReportStats;
  timestamp: string;
}

// Error Types
export interface ApiError {
  message: string;
  code?: string;
  details?: unknown;
}
