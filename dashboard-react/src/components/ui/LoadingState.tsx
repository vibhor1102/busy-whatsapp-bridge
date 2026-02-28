import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
  fullPage?: boolean;
}

export function LoadingState({ size = 'md', text, fullPage }: LoadingStateProps) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };

  const content = (
    <div className="flex flex-col items-center gap-3">
      <Loader2
        className={`${sizes[size]} animate-spin`}
        style={{ color: 'var(--brand-accent)' }}
        aria-hidden="true"
      />
      {text && (
        <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
          {text}
        </p>
      )}
    </div>
  );

  if (fullPage) {
    return (
      <div className="flex items-center justify-center h-96" role="status" aria-live="polite">
        {content}
      </div>
    );
  }

  return content;
}
