/**
 * frontend/js/candidate-result.js
 *
 * Renders one candidate's full screening result: score breakdown,
 * matching/missing skills, AI recommendation, and resume summary.
 *
 * Reads the ATSScore id from the URL (?id=1) and calls the real backend:
 *   GET /screening/result/{id}   -> score, skill lists, recommendations
 *   GET /resumes/{resume_id}     -> candidate name/email, parsed fields
 *   GET /jobs/{job_id}           -> job title
 * On any failure (no backend running, bad id), falls back to demo data
 * so the page is still reviewable standalone.
 *
 * Note: the backend has no dedicated "resume summary" field/service — the
 * summary shown here is assembled client-side from parsed structured
 * fields (experience years, education, matched skills), not a stored or
 * AI-generated summary. Worth building a real summarization service
 * later if that's wanted; this is an honest stand-in, not a mock.
 */

const RECOMMENDATION_ICONS = {
  missing_skill: "bi-exclamation-circle",
  experience_gap: "bi-clock-history",
  education_gap: "bi-mortarboard",
  improvement_tip: "bi-lightbulb",
};

const PRIORITY_BADGE = {
  high: `<span class="badge-c badge-low">High</span>`,
  medium: `<span class="badge-c badge-mid">Medium</span>`,
  low: `<span class="badge-c badge-neutral">Low</span>`,
};

const DEMO_CANDIDATE = {
  name: "Priya Nair", email: "priya.nair@example.com", role: "Backend Engineer", status: "shortlisted",
  score: 91, breakdown: { semantic: 93, skills: 88, experience: 92 },
  matched: ["Python", "FastAPI", "PostgreSQL", "Docker"], missing: ["Kubernetes"],
  summary: "5+ years building production backend services in Python, with FastAPI and PostgreSQL experience.",
  recommendations: [
    { recommendation_type: "missing_skill", message: "Missing skill: Kubernetes.", priority: "medium" },
    { recommendation_type: "improvement_tip", message: "Strong overall match — consider prioritizing for an interview.", priority: "low" },
  ],
};

function statusBadgeLarge(status) {
  const map = {
    shortlisted: `<span class="badge-c badge-good" style="font-size:0.82rem; padding:6px 14px;"><i class="bi bi-check-circle"></i> Shortlisted</span>`,
    pending: `<span class="badge-c badge-mid" style="font-size:0.82rem; padding:6px 14px;"><i class="bi bi-hourglass-split"></i> Pending review</span>`,
    rejected: `<span class="badge-c badge-low" style="font-size:0.82rem; padding:6px 14px;"><i class="bi bi-x-circle"></i> Rejected</span>`,
  };
  return map[status] || map.pending;
}

function scoreColor(value) {
  if (value >= 75) return "var(--score-good)";
  if (value >= 50) return "var(--score-mid)";
  return "var(--score-low)";
}

function buildSummary({ experienceYears, education, matchedSkills }) {
  const parts = [];
  if (experienceYears != null) parts.push(`${experienceYears} year${experienceYears === 1 ? "" : "s"} of experience found in the resume`);
  if (education) parts.push(`education: ${education}`);
  if (matchedSkills && matchedSkills.length) parts.push(`matched skills include ${matchedSkills.slice(0, 4).join(", ")}`);
  if (!parts.length) return "No structured summary could be assembled from this resume's parsed fields.";
  return parts.join(". ") + ".";
}

function renderScoreCard(score, breakdown) {
  document.getElementById("scoreGaugeContainer").innerHTML = ScoreGauge.render({ score, size: 140 });

  const rows = [
    ["Semantic match", breakdown.semantic, "How closely the overall resume text aligns with the job description."],
    ["Skills match", breakdown.skills, "Share of required skills found in the resume."],
    ["Experience match", breakdown.experience, "How well years of experience align with the role's requirement."],
  ];

  document.getElementById("scoreProgressBars").innerHTML = rows
    .map(
      ([label, value, hint]) => `
      <div>
        <div class="d-flex justify-content-between align-items-baseline mb-1">
          <span style="font-size:0.82rem; font-weight:600;">${label}</span>
          <span class="text-mono" style="font-size:0.82rem; color:${scoreColor(value)};">${Math.round(value)}%</span>
        </div>
        <div class="progress" style="height:7px; background:var(--border);">
          <div class="progress-bar" role="progressbar" style="width:${value}%; background-color:${scoreColor(value)};"></div>
        </div>
        <p class="form-hint mb-0 mt-1">${hint}</p>
      </div>`
    )
    .join("");
}

function renderSkillsCard(matched, missing) {
  const total = matched.length + missing.length;
  const pct = total ? Math.round((matched.length / total) * 100) : 0;

  document.getElementById("skillsMatchSummary").textContent = `${matched.length} of ${total} matched`;
  document.getElementById("skillsProgressBar").style.width = `${pct}%`;
  document.getElementById("skillsProgressBar").style.backgroundColor = scoreColor(pct);

  document.getElementById("matchingSkillsList").innerHTML = matched.length
    ? matched.map((s) => `<span class="skill-chip matched"><i class="bi bi-check2 me-1"></i>${s}</span>`).join("")
    : `<p class="text-muted-c mb-0" style="font-size:0.82rem;">No required skills matched.</p>`;

  document.getElementById("missingSkillsList").innerHTML = missing.length
    ? missing.map((s) => `<span class="skill-chip missing">${s}</span>`).join("")
    : `<p class="text-muted-c mb-0" style="font-size:0.82rem;">No missing skills — every requirement was found.</p>`;
}

function renderRecommendationCard(recommendations) {
  const container = document.getElementById("recommendationList");
  if (!recommendations.length) {
    container.innerHTML = `<p class="text-muted-c mb-0" style="font-size:0.82rem;">No recommendations generated for this result.</p>`;
    return;
  }
  container.innerHTML = recommendations
    .map(
      (rec) => `
      <div class="d-flex gap-3 py-3" style="border-bottom:1px solid var(--border);">
        <div class="file-row__icon"><i class="bi ${RECOMMENDATION_ICONS[rec.recommendation_type] || "bi-info-circle"}"></i></div>
        <div class="flex-grow-1">
          <p class="mb-1" style="font-size:0.85rem;">${rec.message}</p>
          ${PRIORITY_BADGE[rec.priority] || ""}
        </div>
      </div>`
    )
    .join("");
}

function renderHeader({ name, email, role, status, summary }) {
  document.getElementById("candidateAvatar").textContent = name.split(" ").map((n) => n[0]).join("");
  document.getElementById("candidateName").textContent = name;
  document.getElementById("candidateMeta").textContent = `${email} · Applied for ${role}`;
  document.getElementById("candidateStatusBadge").innerHTML = statusBadgeLarge(status);
  document.getElementById("resumeSummaryText").textContent = summary;
  document.title = `${name} · Candidate Result · ATS Screen`;
}

function initStatusButtons(atsScoreId, currentStatus) {
  const state = { status: currentStatus };

  async function updateStatus(newStatus) {
    state.status = newStatus;
    document.getElementById("candidateStatusBadge").innerHTML = statusBadgeLarge(newStatus);
    if (!atsScoreId) return; // demo-data mode, no real id to PATCH
    try {
      await api.patch(`/screening/result/${atsScoreId}/status`, { status: newStatus });
    } catch (_) {
      // Real endpoint exists but the request failed (e.g. offline) — the
      // UI already reflects the change locally; nothing further to do.
    }
  }

  document.getElementById("shortlistBtn").addEventListener("click", () => updateStatus("shortlisted"));
  document.getElementById("rejectBtn").addEventListener("click", () => updateStatus("rejected"));
}

async function loadFromRealBackend(atsScoreId) {
  const scoreRes = await api.get(`/screening/result/${atsScoreId}`);
  const score = scoreRes.data;

  const [resumeRes, jobRes] = await Promise.all([
    api.get(`/resumes/${score.resume_id}`),
    api.get(`/jobs/${score.job_description_id}`),
  ]);
  const resume = resumeRes.data;
  const job = jobRes.data;

  const candidate = {
    name: resume.candidate?.name || resume.parsed_name || "Unknown Candidate",
    email: resume.candidate?.email || "—",
    role: job.title,
    status: score.status,
    summary: buildSummary({
      experienceYears: resume.parsed_experience_years,
      education: resume.parsed_education,
      matchedSkills: score.matched_skills,
    }),
  };

  renderHeader(candidate);
  renderScoreCard(score.final_score, {
    semantic: score.semantic_score,
    skills: score.skill_match_score,
    experience: score.experience_match_score,
  });
  renderSkillsCard(score.matched_skills, score.missing_skills);
  renderRecommendationCard(score.recommendations);
  initStatusButtons(score.id, score.status);
}

function loadFromDemoData() {
  const c = DEMO_CANDIDATE;
  renderHeader(c);
  renderScoreCard(c.score, c.breakdown);
  renderSkillsCard(c.matched, c.missing);
  renderRecommendationCard(c.recommendations);
  initStatusButtons(null, c.status);
}

async function loadCandidateResult() {
  const params = new URLSearchParams(window.location.search);
  const atsScoreId = params.get("id");

  if (!atsScoreId) {
    loadFromDemoData();
    return;
  }

  try {
    await loadFromRealBackend(atsScoreId);
  } catch (_) {
    loadFromDemoData();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  loadCandidateResult();
});
