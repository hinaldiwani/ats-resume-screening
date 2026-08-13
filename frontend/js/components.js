/**
 * frontend/js/components.js
 *
 * Shared UI pieces used across every protected page:
 *   - renderSidebar() / renderNavbar(): inject the sidebar and navbar markup
 *     once, instead of duplicating it in every HTML file. Each page just
 *     needs <div id="sidebar-root"></div> and <div id="navbar-root"></div>,
 *     plus body[data-page] / body[data-page-title] attributes.
 *   - ScoreGauge.render(): the signature score-gauge component (SVG ring +
 *     center number + optional sub-bar breakdown), reused on the dashboard
 *     and results pages so a match score always ships with its reasoning.
 */

const NAV_ITEMS = [
  { page: "dashboard", href: "dashboard.html", icon: "bi-speedometer2", label: "Dashboard" },
  { page: "upload-resume", href: "upload-resume.html", icon: "bi-file-earmark-arrow-up", label: "Upload Resume" },
  { page: "post-job", href: "post-job.html", icon: "bi-briefcase", label: "Post Job" },
  { page: "results", href: "results.html", icon: "bi-bar-chart-steps", label: "Screening Results" },
];

function initials(name) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase();
}

function renderSidebar() {
  const root = document.getElementById("sidebar-root");
  if (!root) return;

  const activePage = document.body.dataset.page;
  const user = typeof getCurrentUser === "function" ? getCurrentUser() : null;
  const name = user?.name || "Recruiter";
  const email = user?.email || "";

  const navHtml = NAV_ITEMS.map(
    (item) => `
      <a href="${item.href}" class="sidebar-link ${item.page === activePage ? "active" : ""}">
        <i class="bi ${item.icon}"></i>
        <span>${item.label}</span>
      </a>`
  ).join("");

  root.innerHTML = `
    <div class="offcanvas-lg offcanvas-start sidebar" tabindex="-1" id="sidebar" aria-labelledby="sidebarLabel">
      <div class="d-flex flex-column h-100">
        <div class="sidebar-brand">
          <div class="sidebar-brand__mark">AT</div>
          <div>
            <div class="sidebar-brand__text" id="sidebarLabel">ATS Screen</div>
            <div class="sidebar-brand__sub">HR Console</div>
          </div>
          <button type="button" class="btn-close btn-close-white d-lg-none ms-auto" data-bs-dismiss="offcanvas" data-bs-target="#sidebar" aria-label="Close"></button>
        </div>

        <nav class="sidebar-nav">
          <div class="sidebar-nav__label">Workspace</div>
          ${navHtml}
        </nav>

        <div class="sidebar-footer">
          <div class="sidebar-avatar">${initials(name)}</div>
          <div class="flex-grow-1 overflow-hidden">
            <div class="sidebar-footer__name">${name}</div>
            <div class="sidebar-footer__email">${email}</div>
          </div>
          <button class="sidebar-logout-btn" id="sidebarLogoutBtn" title="Log out" aria-label="Log out">
            <i class="bi bi-box-arrow-right"></i>
          </button>
        </div>
      </div>
    </div>`;

  document.getElementById("sidebarLogoutBtn")?.addEventListener("click", handleLogoutClick);
}

function renderNavbar() {
  const root = document.getElementById("navbar-root");
  if (!root) return;

  const title = document.body.dataset.pageTitle || "Dashboard";
  const user = typeof getCurrentUser === "function" ? getCurrentUser() : null;
  const name = user?.name || "Recruiter";

  root.innerHTML = `
    <header class="app-navbar">
      <button class="navbar-toggle-btn" type="button" data-bs-toggle="offcanvas" data-bs-target="#sidebar" aria-controls="sidebar">
        <i class="bi bi-list fs-5"></i>
      </button>
      <div class="navbar-title">${title}</div>

      <div class="navbar-search">
        <i class="bi bi-search"></i>
        <input type="text" id="globalSearchInput" placeholder="Search candidates, jobs..." />
      </div>

      <div class="navbar-spacer"></div>

      <button class="navbar-icon-btn" title="Notifications" aria-label="Notifications">
        <i class="bi bi-bell"></i>
        <span class="dot"></span>
      </button>

      <div class="dropdown">
        <button class="navbar-user border-0" type="button" data-bs-toggle="dropdown" aria-expanded="false">
          <div class="sidebar-avatar">${initials(name)}</div>
          <span class="navbar-user__name">${name}</span>
          <i class="bi bi-chevron-down small text-secondary-c"></i>
        </button>
        <ul class="dropdown-menu dropdown-menu-end shadow-sm">
          <li><a class="dropdown-item" href="dashboard.html"><i class="bi bi-person me-2"></i>Profile</a></li>
          <li><hr class="dropdown-divider"></li>
          <li><button class="dropdown-item text-danger" id="navbarLogoutBtn"><i class="bi bi-box-arrow-right me-2"></i>Log out</button></li>
        </ul>
      </div>
    </header>`;

  document.getElementById("navbarLogoutBtn")?.addEventListener("click", handleLogoutClick);
}

function handleLogoutClick() {
  // Best-effort server-side revocation (see auth.js docs on why this can
  // fail silently: the token may already be expired, or the backend may
  // be briefly unreachable — the local session is cleared either way).
  const token = getAccessToken();
  if (token) {
    api.post("/auth/logout", { access_token: token }).catch(() => {});
  }
  clearSession();
  window.location.href = "login.html";
}

/**
 * ScoreGauge — the signature visual component. Renders an SVG ring whose
 * fill and color communicate the ATS match score at a glance, plus an
 * optional breakdown of the three sub-scores that produced it.
 *
 * @param {Object} opts
 * @param {number} opts.score - 0-100 final score
 * @param {number} [opts.size=88] - diameter in px
 * @param {Object} [opts.breakdown] - { semantic, skills, experience } each 0-100
 * @returns {string} HTML markup
 */
const ScoreGauge = {
  colorFor(score) {
    if (score >= 75) return { stroke: "var(--score-good)", tint: "score-good" };
    if (score >= 50) return { stroke: "var(--score-mid)", tint: "score-mid" };
    return { stroke: "var(--score-low)", tint: "score-low" };
  },

  render({ score, size = 88, breakdown = null }) {
    const radius = (size - 10) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
    const { stroke } = ScoreGauge.colorFor(score);
    const fontSize = size >= 80 ? 18 : 14;

    const gaugeHtml = `
      <div class="score-gauge" style="width:${size}px;height:${size}px;">
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
          <circle class="track" cx="${size / 2}" cy="${size / 2}" r="${radius}" stroke-width="7"></circle>
          <circle class="value" cx="${size / 2}" cy="${size / 2}" r="${radius}" stroke-width="7"
            stroke="${stroke}"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${offset}"></circle>
        </svg>
        <div class="score-gauge__number" style="font-size:${fontSize}px;">${Math.round(score)}</div>
      </div>`;

    if (!breakdown) return gaugeHtml;

    const rows = [
      ["Semantic", breakdown.semantic],
      ["Skills", breakdown.skills],
      ["Experience", breakdown.experience],
    ]
      .map(
        ([label, value]) => `
        <div class="score-breakdown__row">
          <span class="score-breakdown__label">${label}</span>
          <div class="score-breakdown__bar"><span style="width:${value}%; background:${ScoreGauge.colorFor(value).stroke};"></span></div>
        </div>`
      )
      .join("");

    return `
      <div class="d-flex align-items-center gap-3">
        ${gaugeHtml}
        <div class="score-breakdown">${rows}</div>
      </div>`;
  },
};

document.addEventListener("DOMContentLoaded", () => {
  renderSidebar();
  renderNavbar();
});
