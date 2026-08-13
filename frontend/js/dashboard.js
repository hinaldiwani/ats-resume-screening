/**
 * frontend/js/dashboard.js
 *
 * Populates the dashboard's stat tiles, top-candidates list, and recent
 * activity feed.
 *
 * IMPORTANT: /api/v1/dashboard/* currently has no business logic (see the
 * backend scaffold) — it's an empty router. This file still calls it first,
 * and falls back to realistic demo data on failure, so the page is fully
 * reviewable before that endpoint is implemented. Swap DEMO_* out once
 * dashboard_service.py is built.
 */

const DEMO_STATS = [
  { label: "Open positions", value: "12", icon: "bi-briefcase", tint: "score-good", delta: "+2 this week", up: true },
  { label: "Candidates screened", value: "348", icon: "bi-people", tint: "score-mid", delta: "+41 this week", up: true },
  { label: "Avg. match score", value: "68", icon: "bi-graph-up-arrow", tint: "score-good", delta: "+3 pts", up: true },
  { label: "Awaiting review", value: "27", icon: "bi-hourglass-split", tint: "score-mid", delta: "-5 since Mon", up: false },
];

const DEMO_TOP_CANDIDATES = [
  { name: "Priya Nair", role: "Backend Engineer", score: 91, breakdown: { semantic: 93, skills: 88, experience: 92 } },
  { name: "Marcus Webb", role: "Backend Engineer", score: 84, breakdown: { semantic: 80, skills: 90, experience: 78 } },
  { name: "Sara Chen", role: "Product Designer", score: 79, breakdown: { semantic: 82, skills: 74, experience: 80 } },
  { name: "Tomás Rivera", role: "Data Analyst", score: 63, breakdown: { semantic: 60, skills: 68, experience: 58 } },
];

const DEMO_ACTIVITY = [
  { icon: "bi-file-earmark-check", text: "Resume screened for <strong>Priya Nair</strong> — Backend Engineer", time: "12m ago" },
  { icon: "bi-briefcase", text: "New job posted: <strong>Senior Product Designer</strong>", time: "1h ago" },
  { icon: "bi-check2-circle", text: "<strong>Marcus Webb</strong> shortlisted for Backend Engineer", time: "3h ago" },
  { icon: "bi-upload", text: "6 resumes uploaded to <strong>Data Analyst</strong> pipeline", time: "Yesterday" },
];

// Static demo data only — no backend call for this table, per the request
// that this component ship without any API wiring.
const DEMO_RECENT_RESUMES = [
  { name: "Priya Nair", email: "priya.nair@example.com", fileName: "priya_nair_resume.pdf", fileType: "pdf", role: "Backend Engineer", uploaded: "12m ago", status: "scored" },
  { name: "Marcus Webb", email: "marcus.webb@example.com", fileName: "marcus_webb_cv.docx", fileType: "docx", role: "Backend Engineer", uploaded: "1h ago", status: "scored" },
  { name: "Sara Chen", email: "sara.chen@example.com", fileName: "sara_chen_resume.pdf", fileType: "pdf", role: "Product Designer", uploaded: "3h ago", status: "scored" },
  { name: "Devon Marsh", email: "devon.marsh@example.com", fileName: "devon_marsh_resume.pdf", fileType: "pdf", role: "Data Analyst", uploaded: "Yesterday", status: "processing" },
  { name: "Tomás Rivera", email: "tomas.rivera@example.com", fileName: "tomas_rivera_cv.docx", fileType: "docx", role: "Data Analyst", uploaded: "Yesterday", status: "scored" },
  { name: "Yuki Tanaka", email: "yuki.tanaka@example.com", fileName: "yuki_tanaka_resume.pdf", fileType: "pdf", role: "Backend Engineer", uploaded: "2 days ago", status: "processing" },
];

function renderStats(stats) {
  const container = document.getElementById("statsRow");
  if (!container) return;
  container.innerHTML = stats
    .map(
      (s, i) => `
      <div class="col-6 col-lg-3">
        <div class="stat-tile" style="animation-delay:${i * 60}ms">
          <div class="stat-tile__icon" style="background:var(--${s.tint}-tint); color:var(--${s.tint.replace("score-", "score-")});">
            <i class="bi ${s.icon}"></i>
          </div>
          <div class="stat-tile__value">${s.value}</div>
          <div class="stat-tile__label">${s.label}</div>
          <div class="stat-tile__delta ${s.up ? "up" : "down"}">
            <i class="bi ${s.up ? "bi-arrow-up-short" : "bi-arrow-down-short"}"></i>${s.delta}
          </div>
        </div>
      </div>`
    )
    .join("");
}

function renderTopCandidates(candidates) {
  const container = document.getElementById("topCandidatesList");
  if (!container) return;

  if (!candidates.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon"><i class="bi bi-people"></i></div>
        <h3>No candidates screened yet</h3>
        <p>Upload resumes and post a job to see ranked candidates here.</p>
      </div>`;
    return;
  }

  container.innerHTML = candidates
    .map(
      (c) => `
      <div class="d-flex align-items-center justify-content-between py-3" style="border-bottom:1px solid var(--border);">
        <div class="d-flex align-items-center gap-3">
          <div class="sidebar-avatar" style="background:var(--brand-teal-tint); color:var(--brand-teal-dark);">${c.name.split(" ").map(n => n[0]).join("")}</div>
          <div>
            <div style="font-weight:600; font-size:0.88rem;">${c.name}</div>
            <div class="text-secondary-c" style="font-size:0.78rem;">${c.role}</div>
          </div>
        </div>
        ${ScoreGauge.render({ score: c.score, size: 52 })}
      </div>`
    )
    .join("");
}

function renderActivity(items) {
  const container = document.getElementById("activityList");
  if (!container) return;
  container.innerHTML = items
    .map(
      (a) => `
      <div class="d-flex gap-3 py-3" style="border-bottom:1px solid var(--border);">
        <div class="file-row__icon"><i class="bi ${a.icon}"></i></div>
        <div class="flex-grow-1">
          <div style="font-size:0.84rem;">${a.text}</div>
          <div class="text-muted-c" style="font-size:0.74rem;">${a.time}</div>
        </div>
      </div>`
    )
    .join("");
}

function resumeStatusBadge(status) {
  return status === "scored"
    ? `<span class="badge-c badge-good"><i class="bi bi-check-circle"></i> Scored</span>`
    : `<span class="badge-c badge-mid"><i class="bi bi-hourglass-split"></i> Processing</span>`;
}

function renderRecentResumes(resumes) {
  const container = document.getElementById("recentResumesTableBody");
  if (!container) return;

  if (!resumes.length) {
    container.innerHTML = `<tr><td colspan="5">
      <div class="empty-state">
        <div class="empty-state__icon"><i class="bi bi-inbox"></i></div>
        <h3>No resumes uploaded yet</h3>
        <p>Uploaded resumes will show up here as they come in.</p>
      </div>
    </td></tr>`;
    return;
  }

  container.innerHTML = resumes
    .map(
      (r) => `
      <tr>
        <td>
          <div class="d-flex align-items-center gap-2">
            <div class="sidebar-avatar" style="width:30px;height:30px;font-size:0.72rem; background:var(--brand-teal-tint); color:var(--brand-teal-dark);">${r.name.split(" ").map((n) => n[0]).join("")}</div>
            <div>
              <div style="font-weight:600;">${r.name}</div>
              <div class="text-muted-c" style="font-size:0.76rem;">${r.email}</div>
            </div>
          </div>
        </td>
        <td>
          <div class="d-flex align-items-center gap-2">
            <i class="bi ${r.fileType === "pdf" ? "bi-file-earmark-pdf" : "bi-file-earmark-text"} text-secondary-c"></i>
            <span style="font-size:0.82rem;">${r.fileName}</span>
          </div>
        </td>
        <td style="font-size:0.85rem;">${r.role}</td>
        <td class="text-muted-c" style="font-size:0.8rem;">${r.uploaded}</td>
        <td>${resumeStatusBadge(r.status)}</td>
      </tr>`
    )
    .join("");
}

async function loadDashboard() {
  // Stats
  try {
    const res = await api.get("/dashboard/stats");
    renderStats(res.data);
  } catch (_) {
    renderStats(DEMO_STATS);
  }

  // Top candidates
  try {
    const res = await api.get("/dashboard/top-candidates/all");
    renderTopCandidates(res.data);
  } catch (_) {
    renderTopCandidates(DEMO_TOP_CANDIDATES);
  }

  // Recent activity — no dedicated endpoint in the current API design,
  // demo data only until an /activity endpoint is added.
  renderActivity(DEMO_ACTIVITY);

  // Recent resumes table — static demo data by design, no backend call.
  renderRecentResumes(DEMO_RECENT_RESUMES);
}

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  loadDashboard();
});
