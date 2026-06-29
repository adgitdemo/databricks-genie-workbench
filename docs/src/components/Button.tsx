import React from 'react';
import Link from '@docusaurus/Link';
import clsx from 'clsx';

type Variant = 'primary' | 'navy' | 'outline';

interface ButtonProps {
  to: string;
  children: React.ReactNode;
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary: 'bg-[#eb1600] text-white hover:opacity-90',
  navy: 'bg-[#1b3139] text-white hover:opacity-90',
  outline:
    'bg-transparent text-[#1b3139] dark:text-white border border-[#1b3139] dark:border-white hover:bg-[#1b3139]/5',
};

export default function Button({to, children, variant = 'navy'}: ButtonProps) {
  return (
    <Link
      to={to}
      className={clsx(
        'inline-flex items-center justify-center rounded-md px-6 py-3',
        'text-base font-medium no-underline transition',
        'hover:no-underline',
        variants[variant],
      )}>
      {children}
    </Link>
  );
}
