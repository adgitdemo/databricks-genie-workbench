import React, {type ReactNode} from 'react';
import clsx from 'clsx';
import type {Props} from '@theme/NotFound/Content';
import Button from '@site/src/components/Button';

// Swizzled to brand the catch-all 404 page (build/404.html).
export default function NotFoundContent({className}: Props): ReactNode {
  return (
    <main className={clsx('container margin-vert--xl', className)}>
      <div className="mx-auto flex max-w-3xl flex-col items-center px-4 py-20 text-center">
        <p className="text-sm font-semibold uppercase tracking-wide text-[#2272b4] dark:text-[#4299e0]">
          404
        </p>
        <h1 className="mt-2 text-4xl font-medium md:text-5xl">Page not found</h1>
        <p className="mt-4 text-lg text-slate-600 dark:text-slate-300">
          The page you're looking for doesn't exist or may have moved. Try the
          documentation home, or search with <kbd>⌘</kbd> + <kbd>K</kbd>.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Button to="/" variant="primary">
            Back home
          </Button>
          <Button to="/docs/getting-started/introduction" variant="navy">
            Browse the docs
          </Button>
        </div>
      </div>
    </main>
  );
}
