interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  /** Heading level for `title` - pick whatever's correct for where this
   * card sits in the page's heading hierarchy (e.g. "h2" directly under a
   * page's own h1, "h3" nested under a section's own h2). */
  titleAs?: "h2" | "h3";
}

/** The small "icon + title + one-line description" card introduced on
 * DashboardPage's landing hero - shared here so every page that presents a
 * short list of highlights (capabilities, features) uses the same visual
 * language instead of inventing a new one per page. */
export function FeatureCard({ icon, title, description, titleAs: TitleTag = "h3" }: FeatureCardProps) {
  return (
    <div className="col">
      <div className="card h-100 p-3">
        <i className={`bi ${icon} text-primary fs-4 mb-2`} aria-hidden="true" />
        <TitleTag className="h6 mb-1">{title}</TitleTag>
        <p className="text-secondary small mb-0">{description}</p>
      </div>
    </div>
  );
}
