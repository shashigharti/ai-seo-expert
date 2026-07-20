import { Link, Outlet, useLocation } from "react-router-dom";

/** docs/system-design.md §3's layout shell, interpreted as a lightweight
 * top navbar rather than a full collapsible sidebar - this app has two
 * pages (Expert, About), not enough navigation surface to justify a
 * persistent sidebar yet. */
export function AppLayout() {
  const location = useLocation();
  // A workflow's results live at /workflows/:id (so the page survives a
  // refresh/bookmark - see DashboardPage) - still the "Expert" section, not
  // a separate page, so it must count as active too, not just an exact "/".
  const isExpertRoute = location.pathname === "/" || location.pathname.startsWith("/workflows/");

  return (
    <div className="d-flex flex-column min-vh-100">
      <nav className="navbar navbar-expand bg-white border-bottom">
        <div className="container">
          <Link className="navbar-brand d-flex align-items-center gap-2 fw-semibold" to="/">
            <span className="brand-mark">
              <i className="bi bi-search" aria-hidden="true" />
            </span>
            AISeo Expert
          </Link>
          <div className="navbar-nav">
            <Link
              className={`nav-link d-flex align-items-center gap-1 ${isExpertRoute ? "active" : ""}`}
              to="/"
            >
              <i className="bi bi-speedometer2" aria-hidden="true" />
              Expert
            </Link>
            <Link
              className={`nav-link d-flex align-items-center gap-1 ${location.pathname === "/about" ? "active" : ""}`}
              to="/about"
            >
              <i className="bi bi-info-circle" aria-hidden="true" />
              About
            </Link>
          </div>
        </div>
      </nav>
      <main className="flex-grow-1">
        <Outlet />
      </main>
    </div>
  );
}
