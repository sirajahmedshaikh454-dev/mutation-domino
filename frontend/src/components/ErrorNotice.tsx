import { AlertTriangle, RefreshCw } from 'lucide-react';
import { ApiError } from '../lib/api';

interface ErrorNoticeProps {
  error: unknown;
  title?: string;
  onRetry?: () => void;
}

export function ErrorNotice({ error, title, onRetry }: ErrorNoticeProps) {
  const apiError = error instanceof ApiError ? error : null;
  const message =
    apiError?.message ??
    (error instanceof Error ? error.message : 'An unexpected error occurred.');

  return (
    <div
      role="alert"
      className="flex flex-col gap-4 rounded-2xl border border-rose-200 bg-rose-50/80 p-5 text-rose-900 sm:flex-row sm:items-start"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title ?? 'Something went wrong'}</p>
        <p className="mt-1 text-sm text-rose-800">{message}</p>
        {apiError && (
          <p className="mt-2 font-mono text-[0.7rem] text-rose-700">
            {apiError.code}
            {apiError.status ? ` · HTTP ${apiError.status}` : ''}
          </p>
        )}
      </div>
      {onRetry && (
        <button type="button" className="btn-secondary shrink-0" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Try again
        </button>
      )}
    </div>
  );
}
