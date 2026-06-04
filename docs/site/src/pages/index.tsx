import type {ReactNode} from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Button from '@site/src/components/Button';

const CAPABILITIES = [
  {
    title: 'Create',
    body: 'A multi-turn AI agent walks you from business requirements to a fully configured Genie Space.',
    to: '/docs/features/create-agent',
  },
  {
    title: 'Score',
    body: 'The rule-based IQ Scanner grades space quality across 12 checks and assigns a maturity tier.',
    to: '/docs/features/iq-scanner',
  },
  {
    title: 'Fix',
    body: 'An AI agent reads scan findings and generates targeted JSON patches to close configuration gaps.',
    to: '/docs/features/fix-agent',
  },
  {
    title: 'Optimize',
    body: 'A benchmark-driven pipeline measures real accuracy, diagnoses failures, and iterates to a target.',
    to: '/docs/features/auto-optimize',
  },
  {
    title: 'Track',
    body: 'Every scan, optimization run, and config change is persisted to Lakebase so you can see progress.',
    to: '/docs/platform/operations',
  },
];

const PERSONAS = [
  {
    title: 'Genie Space developer',
    body: 'Build and refine spaces. Start with the Create Agent and the IQ Scanner.',
    to: '/docs/getting-started/introduction',
  },
  {
    title: 'Workspace admin',
    body: 'Deploy and operate the Workbench. Start with the Deployment Guide and the auth model.',
    to: '/docs/getting-started/deployment-guide',
  },
  {
    title: 'Contributor',
    body: 'Extend the codebase. Start with the Architecture Overview, then the relevant feature doc.',
    to: '/docs/getting-started/architecture-overview',
  },
];

function Hero() {
  const {siteConfig} = useDocusaurusContext();
  const logo = useBaseUrl('img/logo.svg');
  return (
    <header className="w-full bg-[#1b3139] text-white">
      <div className="mx-auto flex max-w-5xl flex-col items-center px-4 py-20 text-center md:px-10 md:py-28">
        <img src={logo} alt="Genie Workbench" className="mb-8 w-20 md:w-24" />
        <h1 className="text-4xl font-medium leading-tight md:text-5xl">
          {siteConfig.title}
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-300 md:text-xl">
          {siteConfig.tagline}. A unified developer tool deployed as a
          Databricks App — with on-behalf-of auth, Lakebase persistence, and a
          benchmark-driven optimization pipeline.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Button to="/docs/getting-started/introduction" variant="primary">
            Get Started
          </Button>
          <Button to="/docs/getting-started/deployment-guide" variant="navy">
            Deploy
          </Button>
          <Link
            href={`https://github.com/${siteConfig.organizationName}/${siteConfig.projectName}`}
            className="text-slate-200 underline-offset-4 hover:underline">
            View on GitHub →
          </Link>
        </div>
      </div>
    </header>
  );
}

function CardGrid({
  eyebrow,
  heading,
  items,
}: {
  eyebrow: string;
  heading: string;
  items: {title: string; body: string; to: string}[];
}) {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 md:px-10">
      <p className="text-sm font-semibold uppercase tracking-wide text-[#2272b4] dark:text-[#4299e0]">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-3xl font-normal">{heading}</h2>
      <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <Link
            key={item.title}
            to={item.to}
            className="group rounded-xl border border-slate-200 bg-white p-6 no-underline transition hover:border-[#2272b4] hover:shadow-md hover:no-underline dark:border-slate-700 dark:bg-[#1f3239] dark:hover:border-[#4299e0]">
            <h3 className="text-xl font-medium text-[#1b3139] group-hover:text-[#2272b4] dark:text-white dark:group-hover:text-[#4299e0]">
              {item.title}
            </h3>
            <p className="mt-2 text-slate-600 dark:text-slate-300">
              {item.body}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title="Documentation"
      description={siteConfig.tagline}>
      <Hero />
      <main>
        <CardGrid
          eyebrow="The continuous-improvement loop"
          heading="Five capabilities, one workflow"
          items={CAPABILITIES}
        />
        <div className="border-t border-slate-200 dark:border-slate-800">
          <CardGrid
            eyebrow="Start here"
            heading="Choose your path"
            items={PERSONAS}
          />
        </div>
      </main>
    </Layout>
  );
}
