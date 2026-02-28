import { Suspense } from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import { Loading } from '../components/ui/Loading';

interface LazyPageProps {
  children: React.ReactNode;
}

export function LazyPage({ children }: LazyPageProps) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<Loading fullPage text="Loading page..." />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  );
}
