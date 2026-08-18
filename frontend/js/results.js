/**
 * frontend/js/results.js
 *
 * Renders the ranked candidate list for a job, with the score-gauge
 * component, matched/missing skill chips, status filtering, and
 * shortlist/reject actions.
 *
 * Attempts /api/v1/screening/results/{job_id} first; that route has no
 * business logic yet, so a failed request falls back to demo data —
 * clearly separated below — so the page is fully reviewable on its own.
 */

const DEMO_RESULTS = [
  {
    id: 1, name: "Priya Nair", email: "priya.nair@example.com", score: 91,
    breakdown: { semantic: 93, skills: 88, experience: 92 },
    matched: ["Python", "FastAPI", "PostgreSQL", "Docker"], missing: ["Kubernetes"],
    status: "shortlisted",
  },
  {
    id: 2, name: "Marcus Webb", email: "marcus.webb@example.com", score: 84,
    breakdown: { semantic: 80, skills: 90, experience: 78 },
    matched: ["Python", "FastAPI", "Docker", "Kubernetes"], missing: ["PostgreSQL"],
    status: "pending",
  },
  {
    id: 3, name: "Elena Petrova", email: "elena.p@example.com", score: 77,
    breakdown: { semantic: 76, skills: 72, experience: 84 },
    matched: ["Python", "PostgreSQL"], missing: ["FastAPI", "Docker"],
    status: "pending",
  },
  {
    id: 4, name: "Tomás Rivera", email: "tomas.r@example.com", score: 58,
    breakdown: { semantic: 55, skills: 60, experience: 58 },
    matched: ["Python"], missing: ["FastAPI", "PostgreSQL", "Docker"],
    status: "pending",
  },
  {
    id: 5, name: "Yuki Tanaka", email: "yuki.t@example.com", score: 41,
    breakdown: { semantic: 38, skills: 45, experience: 40 },
    matched: [], missing: ["Python", "FastAPI", "PostgreSQL", "Docker"],
    status: "rejected",
  },
];

let allResults = [];
let currentFilter = "all";
let currentSort = "score-desc";

function statusBadge(status) {
  const map = {
    shortlisted: `<span class="badge-c badge-good"><i class="bi bi-check-circle"></i> Shortlisted</span>`,
    pending: `<span class="badge-c badge-mid"><i class="bi bi-hourglass-split"></i> Pending</span>`,
    rejected: `<span class="badge-c badge-low"><i class="bi bi-x-circle"></i> Rejected</span>`,
  };
  return map[status] || map.pending;
}

function renderResults() {
  const container = document.getElementById("resultsTableBody");
  const emptyState = document.getElementById("resultsEmptyState");
  const countLabel = document.getElementById("resultsCount");

  let filtered = currentFilter === "all" ? allResults : allResults.filter((r) => r.status === currentFilter);

  filtered = [...filtered].sort((a, b) =>
    currentSort === "score-desc" ? b.score - a.score : a.score - b.score
  );

  if (countLabel) countLabel.textContent = `${filtered.length} candidate${filtered.length !== 1 ? "s" : ""}`;

  if (filtered.length === 0) {
    container.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }
  emptyState.style.display = "none";

  container.innerHTML = filtered
    .map(
      (r) => `
      <tr>
        <td>${ScoreGauge.render({ score: r.score, size: 56, breakdown: r.breakdown })}</td>
        <td>
          <div style="font-weight:600;">${r.name}</div>
          <div class="text-muted-c" style="font-size:0.78rem;">${r.email}</div>
        </td>
        <td style="max-width:260px;">
          ${r.matched.map((s) => `<span class="skill-chip matched">${s}</span>`).join("")}
          ${r.missing.map((s) => `<span class="skill-chip missing">${s}</span>`).join("")}
        </td>
        <td>${statusBadge(r.status)}</td>
        <td class="text-end">
          <div class="d-flex gap-2 justify-content-end">
            <a href="candidate-result.html?id=${r.id}" class="btn-ghost-sm" title="View details"><i class="bi bi-eye"></i></a>
            <button class="btn-ghost-sm" onclick="updateStatus(${r.id}, 'shortlisted')" title="Shortlist"><i class="bi bi-check2"></i></button>
            <button class="btn-ghost-sm" onclick="updateStatus(${r.id}, 'rejected')" title="Reject"><i class="bi bi-x"></i></button>
          </div>
        </td>
      </tr>`
    )
    .join("");
}

async function updateStatus(id, status) {
  const record = allResults.find((r) => r.id === id);
  if (!record) return;
  record.status = status;
  renderResults();

  try {
    await api.patch(`/screening/result/${id}/status`, { status });
  } catch (_) {
    // /screening/result/{id}/status has no backend logic yet — the local
    // UI state above still reflects the recruiter's action.
  }
}

function initFilters() {
  document.querySelectorAll("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-filter]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderResults();
    });
  });

  document.getElementById("sortSelect")?.addEventListener("change", (e) => {
    currentSort = e.target.value;
    renderResults();
  });

  document.getElementById("resultsSearchInput")?.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    const rows = document.querySelectorAll("#resultsTableBody tr");
    rows.forEach((row) => {
      row.style.display = row.textContent.toLowerCase().includes(q) ? "" : "none";
    });
  });
}

async function loadResults() {
  try {
    const res = await api.get("/screening/results/all");
    allResults = res.data;
  } catch (_) {
    allResults = DEMO_RESULTS;
  }
  renderResults();
}

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  initFilters();
  loadResults();
});
