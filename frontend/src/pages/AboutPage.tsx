import { FeatureCard } from "../components/common/FeatureCard";
import { PageHeader } from "../components/layout/PageHeader";

const CAPABILITIES = [
  {
    icon: "bi-signpost-2",
    title: "Technical SEO",
    description: "Crawlability, sitemaps, canonical tags, redirects.",
  },
  {
    icon: "bi-tags",
    title: "Metadata",
    description: "Page titles, meta descriptions, social sharing tags.",
  },
  {
    icon: "bi-file-text",
    title: "Content",
    description: "Heading structure, content depth, internal linking.",
  },
  {
    icon: "bi-universal-access",
    title: "Accessibility",
    description: "Alt text, semantic HTML, contrast, keyboard navigation.",
  },
  {
    icon: "bi-speedometer",
    title: "Performance",
    description: "Core Web Vitals, image weight, render-blocking resources.",
  },
];

/** docs/specs.md's Information Architecture: an "About" section explaining
 * purpose, architecture, and the multi-agent workflow simply enough for a
 * non-technical reader. Static content, no backend dependency.
 *
 * Same visual language as DashboardPage's landing hero - plain, borderless
 * heading/subtitle (PageHeader) and the same FeatureCard grid for a short
 * list of highlights, rather than each page inventing its own look. */
export function AboutPage() {
  return (
    <div className="container py-5">
      <PageHeader
        title="About AISeo Expert"
        subtitle="What this tool does and how it works, in plain terms."
      />

      <div className="card p-4 shadow-sm mb-4">
        <h2 className="h5 d-flex align-items-center gap-2">
          <i className="bi bi-bullseye text-primary" aria-hidden="true" />
          Purpose
        </h2>
        <p className="mb-0">
          AISeo Expert scans a GitHub repository's source files for SEO issues - things like missing
          page titles, broken crawl rules, slow-loading images, or accessibility gaps that also hurt
          search rankings - and can open a pull request that fixes the ones you approve.
        </p>
      </div>

      <div className="card p-4 shadow-sm mb-4">
        <h2 className="h5 d-flex align-items-center gap-2">
          <i className="bi bi-diagram-3 text-primary" aria-hidden="true" />
          How it works
        </h2>
        <p>
          Rather than one program trying to check everything, the work is split across several
          specialized AI agents, each focused on one area:
        </p>
        <div className="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-3">
          {CAPABILITIES.map((capability) => (
            <FeatureCard key={capability.title} {...capability} />
          ))}
        </div>
      </div>

      <div className="card p-4 shadow-sm mb-4">
        <h2 className="h5 d-flex align-items-center gap-2">
          <i className="bi bi-list-ol text-primary" aria-hidden="true" />
          The workflow
        </h2>
        <ol className="mb-0">
          <li>A manager agent decides which specialists are relevant to a full audit.</li>
          <li>Each specialist examines the repository and reports findings with evidence.</li>
          <li>Low-confidence findings get a second opinion from a reviewer agent before you see them.</li>
          <li>You review the findings and approve the ones you want fixed.</li>
          <li>A fix agent proposes the code change and opens a pull request on your repository.</li>
        </ol>
      </div>

      <div className="card p-4 shadow-sm mb-4">
        <h2 className="h5 d-flex align-items-center gap-2">
          <i className="bi bi-cpu text-primary" aria-hidden="true" />
          AI models
        </h2>
        <p className="mb-0">
          Agents run on Qwen Cloud models (Alibaba Cloud's DashScope). Tasks that need real
          reasoning - weighing evidence, judging severity, drafting a fix - run on a larger model
          with its thinking mode enabled; simpler, more mechanical checks run on a smaller, faster
          one. Where thinking mode was used, you can expand an agent's own reasoning trace to see
          exactly how it reached its conclusion, alongside its token usage and estimated cost, shown
          live as agents run.
        </p>
      </div>

      <div className="card p-4 shadow-sm">
        <h2 className="h5 d-flex align-items-center gap-2">
          <i className="bi bi-github text-primary" aria-hidden="true" />
          GitHub integration
        </h2>
        <p className="mb-0">
          The repository you point AISeo Expert at is read directly via GitHub's API - no separate
          upload step. When you approve fixes, a new branch and pull request are opened on that same
          repository, so review and merge happen through GitHub exactly as they normally would. In
          this hackathon build, PR generation uses one GitHub token scoped to repositories that
          account owns - see the Roadmap on the front page for connecting your own account instead.
        </p>
      </div>
    </div>
  );
}
