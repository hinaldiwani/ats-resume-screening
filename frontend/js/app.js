// --- State Management ---
const API_BASE = "/api";
let token = localStorage.getItem("ats_token") || "";
let currentUser = JSON.parse(localStorage.getItem("ats_user") || "null");
let selectedFiles = [];
let activeAuthMode = "login";
let currentJobs = [];
let currentRankings = [];

// --- Authenticated Fetch Helper ---
async function authFetch(url, options = {}) {
  if (!token) {
    token = "";
    currentUser = null;
    localStorage.removeItem("ats_token");
    localStorage.removeItem("ats_user");
    updateAuthUI();
    openAuthModal("login");
    throw new Error("Authentication required. Please sign in.");
  }

  const headers = { ...(options.headers || {}) };
  headers["Authorization"] = `Bearer ${token}`;
  options.headers = headers;

  try {
    const res = await fetch(url, options);
    if (res.status === 401) {
      // Session expired or unauthenticated
      token = "";
      currentUser = null;
      localStorage.removeItem("ats_token");
      localStorage.removeItem("ats_user");
      updateAuthUI();
      openAuthModal("login");
      throw new Error("Authentication required. Please sign in.");
    }
    return res;
  } catch (err) {
    throw err;
  }
}


// --- Toast Notifications ---
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle-fill' : 'exclamation-triangle-fill'}"></i> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// --- Circular Gauge Renderer ---
function renderCircularScore(score) {
  const numScore = Math.min(100, Math.max(0, Math.round(score || 0)));
  const scoreClass = numScore >= 78 ? "high" : (numScore >= 58 ? "medium" : "low");
  const color = numScore >= 78 ? "#10b981" : (numScore >= 58 ? "#f59e0b" : "#ef4444");
  const strokeDash = `${numScore}, 100`;

  return `
    <div class="circular-score-wrapper ${scoreClass}" title="${numScore}% Overall Match">
      <svg class="circular-chart" viewBox="0 0 36 36">
        <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <path class="circle" stroke="${color}" stroke-dasharray="${strokeDash}" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
        <text x="18" y="20.35" class="percentage-text" fill="${color}">${numScore}%</text>
      </svg>
    </div>
  `;
}

// --- Navigation & View Switching ---
function switchView(viewName) {
  if (!token || !currentUser) {
    showToast("Please sign in to access the recruiter portal.", "error");
    openAuthModal("login");
    return;
  }

  document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(btn => btn.classList.remove("active"));

  const targetSec = document.getElementById(`view-${viewName}`);
  if (targetSec) targetSec.classList.add("active");

  const navBtns = document.querySelectorAll(".nav-item");
  navBtns.forEach(b => {
    if (b.getAttribute("onclick") && b.getAttribute("onclick").includes(viewName)) {
      b.classList.add("active");
    }
  });

  if (viewName === "dashboard") loadDashboard();
  else if (viewName === "jobs") loadJobs();
  else if (viewName === "upload") loadUploadJobsDropdown();
  else if (viewName === "candidates") loadRankingJobsDropdown();
  else if (viewName === "reports") loadReports();
}

// --- Status Filter Navigation from Dashboard ---
async function navigateToCandidatesWithStatus(status) {
  if (!token || !currentUser) {
    showToast("Please sign in to access candidates.", "error");
    openAuthModal("login");
    return;
  }

  switchView("candidates");
  const statusFilterSelect = document.getElementById("rankingStatusFilter");
  if (statusFilterSelect) {
    statusFilterSelect.value = status;
  }
  await loadRankingJobsDropdown();
  filterAndSortCandidateRankings();
}

// --- Quick Action Handlers ---
function handleQuickAction(action) {
  if (!token || !currentUser) {
    showToast("Please sign in to access recruiter actions.", "error");
    openAuthModal("login");
    return;
  }

  if (action === "create-job") {
    switchView("jobs");
    setTimeout(() => {
      openJobModal();
    }, 50);
    try { window.history.pushState({}, "", "/jobs/create"); } catch (e) {}
  } else if (action === "upload-resumes") {
    switchView("upload");
    try { window.history.pushState({}, "", "/resumes/upload"); } catch (e) {}
  } else if (action === "view-candidates") {
    switchView("candidates");
    try { window.history.pushState({}, "", "/candidates"); } catch (e) {}
  } else if (action === "view-reports") {
    switchView("reports");
    try { window.history.pushState({}, "", "/reports"); } catch (e) {}
  }
}

function setupQuickActions() {
  const actionsMap = [
    { id: "qa-create-job", action: "create-job" },
    { id: "qa-upload-resumes", action: "upload-resumes" },
    { id: "qa-view-candidates", action: "view-candidates" },
    { id: "qa-view-reports", action: "view-reports" },
    { id: "quick-action-create-job", action: "create-job" },
    { id: "quick-action-upload-resumes", action: "upload-resumes" },
    { id: "quick-action-view-candidates", action: "view-candidates" },
    { id: "quick-action-view-reports", action: "view-reports" }
  ];

  actionsMap.forEach(({ id, action }) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.cursor = "pointer";
      el.setAttribute("role", "button");
      el.setAttribute("tabindex", "0");
      el.onclick = (e) => {
        if (e) e.stopPropagation();
        handleQuickAction(action);
      };
      el.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (e) e.stopPropagation();
          handleQuickAction(action);
        }
      };
    }
  });

  // Also query any quick action card dynamically
  document.querySelectorAll(".quick-action-card").forEach(card => {
    card.style.cursor = "pointer";
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    const id = card.id || "";
    let action = null;
    if (id.includes("create-job")) action = "create-job";
    else if (id.includes("upload")) action = "upload-resumes";
    else if (id.includes("candidates")) action = "view-candidates";
    else if (id.includes("reports")) action = "view-reports";
    if (action) {
      card.onclick = (e) => {
        if (e) e.stopPropagation();
        handleQuickAction(action);
      };
      card.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (e) e.stopPropagation();
          handleQuickAction(action);
        }
      };
    }
  });
}

function scrollToQuickActions() {
  const sec = document.getElementById("quickActionsSection");
  if (sec) {
    sec.scrollIntoView({ behavior: "smooth", block: "start" });
    sec.style.transition = "box-shadow 0.3s ease, border-color 0.3s ease";
    sec.style.borderColor = "var(--primary)";
    sec.style.boxShadow = "0 0 25px rgba(79, 140, 255, 0.4)";
    setTimeout(() => {
      sec.style.borderColor = "";
      sec.style.boxShadow = "";
    }, 1500);
  }
}

// --- Auth Handling ---
function updateAuthUI() {
  const profileArea = document.getElementById("userProfileArea");
  const navLinks = document.getElementById("navLinks");

  if (token && currentUser) {
    if (navLinks) navLinks.style.display = "flex";
    if (profileArea) {
      profileArea.innerHTML = `
        <div class="user-profile">
          <div class="user-avatar">${(currentUser.full_name || 'U').charAt(0).toUpperCase()}</div>
          <div style="font-size: 0.85rem;">
            <div style="font-weight: 700; color: #ffffff;">${currentUser.full_name || 'Recruiter'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${currentUser.role || 'Recruiter'}</div>
          </div>
          <button class="btn btn-outline btn-sm" onclick="logout()"><i class="bi bi-box-arrow-right"></i> Logout</button>
        </div>
      `;
    }
  } else {
    if (navLinks) navLinks.style.display = "none";
    if (profileArea) {
      profileArea.innerHTML = `
        <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')"><i class="bi bi-box-arrow-in-right"></i> Sign In / Register</button>
      `;
    }
    resetViewData();
  }
}

function resetViewData() {
  currentJobs = [];
  currentRankings = [];
  selectedFiles = [];

  const statJobs = document.getElementById("stat-total-jobs");
  if (statJobs) statJobs.innerText = "0";
  const statResumes = document.getElementById("stat-total-resumes");
  if (statResumes) statResumes.innerText = "0";
  const statScreened = document.getElementById("stat-screened-candidates");
  if (statScreened) statScreened.innerText = "0";
  const statShortlisted = document.getElementById("stat-shortlisted");
  if (statShortlisted) statShortlisted.innerText = "0";
  const statRejected = document.getElementById("stat-rejected");
  if (statRejected) statRejected.innerText = "0";
  const statAvg = document.getElementById("stat-avg-score");
  if (statAvg) statAvg.innerText = "0%";

  const jobsContainer = document.getElementById("dashboard-jobs-container");
  if (jobsContainer) {
    jobsContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon primary"><i class="bi bi-shield-lock"></i></div>
        <h3 class="empty-state-title">Authentication Required</h3>
        <p class="empty-state-desc">Please sign in to view your recruitment pipelines and active jobs.</p>
        <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')"><i class="bi bi-box-arrow-in-right"></i> Sign In</button>
      </div>
    `;
  }

  const candContainer = document.getElementById("dashboard-candidates-container");
  if (candContainer) {
    candContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon success"><i class="bi bi-shield-lock"></i></div>
        <h3 class="empty-state-title">Authentication Required</h3>
        <p class="empty-state-desc">Please sign in to view candidate screening rankings.</p>
        <button class="btn btn-primary btn-sm" onclick="openAuthModal('login')"><i class="bi bi-box-arrow-in-right"></i> Sign In</button>
      </div>
    `;
  }

  const jobsGrid = document.getElementById("jobsGrid");
  if (jobsGrid) {
    jobsGrid.innerHTML = `
      <div class="empty-state" style="grid-column: 1/-1;">
        <div class="empty-state-icon primary"><i class="bi bi-shield-lock"></i></div>
        <h3 class="empty-state-title">Authentication Required</h3>
        <p class="empty-state-desc">Sign in to manage your jobs and candidate pipelines.</p>
        <button class="btn btn-primary" onclick="openAuthModal('login')"><i class="bi bi-box-arrow-in-right"></i> Sign In</button>
      </div>
    `;
  }

  const rankTbody = document.getElementById("candidateRankingsTbody");
  if (rankTbody) {
    rankTbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">Sign in to view candidate rankings and ATS scores.</td></tr>`;
  }
}

function openAuthModal(mode = "login") {
  activeAuthMode = mode;
  toggleAuthTab(mode);
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.add("active");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("active");
}

function toggleAuthTab(mode) {
  activeAuthMode = mode;
  const tabLogin = document.getElementById("tabLogin");
  const tabReg = document.getElementById("tabRegister");
  const nameGrp = document.getElementById("fullNameGroup");
  const submitBtn = document.getElementById("authSubmitBtn");
  const title = document.getElementById("authModalTitle");

  if (mode === "login") {
    if (tabLogin) tabLogin.classList.add("active");
    if (tabReg) tabReg.classList.remove("active");
    if (nameGrp) nameGrp.style.display = "none";
    if (submitBtn) submitBtn.innerText = "Sign In";
    if (title) title.innerText = "Recruiter Login";
  } else {
    if (tabReg) tabReg.classList.add("active");
    if (tabLogin) tabLogin.classList.remove("active");
    if (nameGrp) nameGrp.style.display = "block";
    if (submitBtn) submitBtn.innerText = "Create Account";
    if (title) title.innerText = "Recruiter Registration";
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value.trim();
  const fullName = document.getElementById("authFullName") ? document.getElementById("authFullName").value.trim() : "";

  const endpoint = activeAuthMode === "login" ? `${API_BASE}/login` : `${API_BASE}/register`;
  const bodyData = activeAuthMode === "login"
    ? { email, username: email, password }
    : { email, username: email, password, full_name: fullName, role: "Recruiter" };

  const submitBtn = document.getElementById("authSubmitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Authenticating...";
  }

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bodyData)
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Authentication failed");

    token = data.access_token;
    currentUser = data.user;
    localStorage.setItem("ats_token", token);
    localStorage.setItem("ats_user", JSON.stringify(currentUser));

    updateAuthUI();
    closeModal("authModal");
    showToast(`Welcome, ${currentUser.full_name}!`);

    document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
    const dashSec = document.getElementById("view-dashboard");
    if (dashSec) dashSec.classList.add("active");
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = activeAuthMode === "login" ? "Sign In" : "Create Account";
    }
  }
}

function logout() {
  token = "";
  currentUser = null;
  localStorage.removeItem("ats_token");
  localStorage.removeItem("ats_user");
  updateAuthUI();
  document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
  const pubSec = document.getElementById("view-public");
  if (pubSec) pubSec.classList.add("active");
  showToast("Logged out successfully");
  openAuthModal("login");
}


// --- Dashboard Data Loading ---
async function loadDashboard() {
  if (!token || !currentUser) {
    resetViewData();
    openAuthModal("login");
    return;
  }

  // 1. Stats Loading (Isolated)
  try {
    const res = await authFetch(`${API_BASE}/dashboard/stats`);
    if (res && res.ok) {
      const stats = await res.json();
      const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.innerText = val;
      };
      setEl("stat-total-jobs", stats.total_jobs ?? 0);
      setEl("stat-total-resumes", stats.total_resumes ?? 0);
      setEl("stat-screened-candidates", stats.screened_candidates ?? 0);
      setEl("stat-shortlisted", stats.shortlisted_candidates ?? 0);
      setEl("stat-rejected", stats.rejected_candidates ?? 0);
      setEl("stat-avg-score", `${stats.average_ats_score ?? 0}%`);
    }
  } catch (err) {
    console.error("Dashboard stats error:", err);
  }

  // 2. Recent Jobs Loading (Isolated)
  try {
    const jobsRes = await authFetch(`${API_BASE}/jobs`);
    if (jobsRes && jobsRes.ok) {
      currentJobs = await jobsRes.json();
      renderDashboardJobs(currentJobs);
    } else {
      renderDashboardJobs([]);
    }
  } catch (err) {
    console.error("Dashboard jobs error:", err);
    renderDashboardJobs([]);
  }

  // 3. Recent Screened Candidates Loading (Isolated with Fallback)
  try {
    let recentCandidates = [];
    const candRes = await authFetch(`${API_BASE}/dashboard/recent-candidates`);
    if (candRes && candRes.ok) {
      recentCandidates = await candRes.json();
    }

    // Fallback: if recent-candidates returned empty or non-array, attempt /screening/all
    if (!Array.isArray(recentCandidates) || recentCandidates.length === 0) {
      const allRes = await authFetch(`${API_BASE}/screening/all?status_filter=All`);
      if (allRes && allRes.ok) {
        const allScreenings = await allRes.json();
        if (Array.isArray(allScreenings) && allScreenings.length > 0) {
          recentCandidates = allScreenings.map(s => {
            const matchedJob = (currentJobs || []).find(j => j.id === s.job_id);
            return {
              screening_id: s.id,
              candidate_id: s.candidate_id || s.id,
              candidate_name: s.candidate_name || "Candidate",
              candidate_email: s.candidate_email || "",
              job_id: s.job_id,
              job_title: s.job_title || (matchedJob ? matchedJob.title : "Target Role"),
              overall_score: s.overall_score || 0,
              skills_score: s.skills_score || 0,
              experience_score: s.experience_score || 0,
              education_score: s.education_score || 0,
              status: s.status || "Maybe",
              recommendation: s.recommendation || "Evaluated Fit",
              created_at: s.created_at
            };
          });
        }
      }
    }

    renderDashboardCandidates(recentCandidates);
  } catch (err) {
    console.error("Dashboard candidates error:", err);
    renderDashboardCandidates([]);
  }

  // Initialize and bind quick action click listeners
  setupQuickActions();
}

function renderDashboardJobs(jobs) {
  const container = document.getElementById("dashboard-jobs-container");
  if (!container) return;

  if (!jobs || jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon primary"><i class="bi bi-briefcase"></i></div>
        <h3 class="empty-state-title">No jobs created yet</h3>
        <p class="empty-state-desc">You haven't posted any job openings. Create a job to begin screening resumes.</p>
        <button class="btn btn-primary btn-sm" onclick="openJobModal()"><i class="bi bi-plus-lg"></i> Create New Job</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Job Title</th>
            <th>Dept</th>
            <th>Resumes</th>
            <th>Shortlisted</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="dashboard-jobs-tbody">
          ${jobs.slice(0, 5).map(j => `
            <tr>
              <td style="font-weight: 700; color: #ffffff;">${j.title}</td>
              <td>${j.department}</td>
              <td><span class="score-badge info">${j.total_resumes || 0}</span></td>
              <td><span class="score-badge high">${j.shortlisted_count || 0}</span></td>
              <td>
                <button class="btn btn-outline btn-sm" onclick="viewJobDetail(${j.id})"><i class="bi bi-eye"></i> Screen</button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderDashboardCandidates(candidates) {
  const container = document.getElementById("dashboard-candidates-container");
  if (!container) return;

  if (!candidates || !Array.isArray(candidates) || candidates.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon success"><i class="bi bi-people"></i></div>
        <h3 class="empty-state-title">No candidates screened yet</h3>
        <p class="empty-state-desc">Upload candidate resumes to see automated ATS rankings, scores, and classifications here.</p>
        <button class="btn btn-primary btn-sm" onclick="switchView('upload')"><i class="bi bi-cloud-arrow-up-fill"></i> Upload Resumes</button>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="table-container">
      <table class="table">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Job Target</th>
            <th>ATS Score</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="dashboard-candidates-tbody">
          ${candidates.slice(0, 5).map(c => {
            const numScore = Math.min(100, Math.max(0, Math.round(parseFloat(c.overall_score) || 0)));
            const badgeClass = numScore >= 75 ? "high" : (numScore >= 50 ? "medium" : "low");
            const statusClass = (c.status || "maybe").toLowerCase();
            const candId = c.candidate_id || c.id || 0;
            return `
              <tr>
                <td>
                  <div style="font-weight: 700; color: #ffffff;">${c.candidate_name || 'Candidate'}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted);">${c.candidate_email || 'No email'}</div>
                </td>
                <td style="font-size: 0.825rem; color: var(--text-muted);">${c.job_title || 'Target Role'}</td>
                <td><span class="score-badge ${badgeClass}">${numScore}%</span></td>
                <td><span class="status-badge ${statusClass}">${c.status || 'Evaluated'}</span></td>
                <td>
                  <button class="btn btn-outline btn-sm" onclick="viewCandidateProfile(${candId})"><i class="bi bi-person-lines-fill"></i> View</button>
                </td>
              </tr>
            `;
          }).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// --- Job Management ---
async function loadJobs() {
  if (!token || !currentUser) return;
  try {
    const res = await authFetch(`${API_BASE}/jobs`);
    if (res.ok) {
      currentJobs = await res.json();
      renderJobsGrid(currentJobs);
    }
  } catch (err) {
    console.error("Error loading jobs:", err);
  }
}

function renderJobsGrid(jobs) {
  const grid = document.getElementById("jobsGrid");
  if (!grid) return;

  if (!jobs || jobs.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column: 1/-1;">
        <div class="empty-state-icon primary"><i class="bi bi-briefcase"></i></div>
        <h3 class="empty-state-title">No jobs created yet</h3>
        <p class="empty-state-desc">You haven't posted any job openings. Create a job position to begin uploading and screening candidate resumes.</p>
        <button class="btn btn-primary" onclick="openJobModal()"><i class="bi bi-plus-lg"></i> Create New Job</button>
      </div>
    `;
    return;
  }

  grid.innerHTML = jobs.map(j => {
    const reqSkills = (j.required_skills_text || "").split(",").filter(s => s.trim());
    return `
      <div class="job-card">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <span class="job-badge ${(j.status || 'open').toLowerCase()}">${j.status}</span>
            <span style="font-size: 0.8rem; color: var(--text-muted);"><i class="bi bi-geo-alt"></i> ${j.location}</span>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 0.25rem; color: #ffffff;">${j.title}</h3>
          <div style="font-size: 0.825rem; color: var(--text-muted); margin-bottom: 0.75rem;">${j.department} • Min ${j.min_experience} yrs exp</div>
          
          <div style="margin-bottom: 1rem;">
            ${reqSkills.slice(0, 5).map(s => `<span class="skill-pill required"><i class="bi bi-check-circle-fill"></i> ${s.trim()}</span>`).join("")}
          </div>
        </div>

        <div style="border-top: 1px solid var(--border); pt-3; margin-top: 1rem; padding-top: 1rem; display: flex; justify-content: space-between; align-items: center;">
          <div style="font-size: 0.85rem; color: var(--text-muted);">
            <strong style="color: #ffffff;">${j.total_resumes || 0}</strong> Resumes Screened
          </div>
          <div style="display: flex; gap: 0.4rem;">
            <button class="btn btn-outline btn-sm" onclick="openJobModal(${j.id})"><i class="bi bi-pencil"></i> Edit</button>
            <button class="btn btn-primary btn-sm" onclick="viewJobDetail(${j.id})"><i class="bi bi-people"></i> Screen</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function openJobModal(jobId = null) {
  if (!token) {
    showToast("Please login to create or edit jobs.", "error");
    openAuthModal("login");
    return;
  }

  const form = document.getElementById("jobForm");
  if (form) form.reset();
  const idInput = document.getElementById("jobIdInput");
  if (idInput) idInput.value = "";

  if (jobId) {
    const job = currentJobs.find(j => j.id === jobId);
    if (job) {
      document.getElementById("jobModalTitle").innerText = "Edit Job Posting";
      document.getElementById("jobIdInput").value = job.id;
      document.getElementById("jobTitle").value = job.title;
      document.getElementById("jobDepartment").value = job.department;
      document.getElementById("jobDescription").value = job.description;
      document.getElementById("jobReqSkills").value = job.required_skills_text || "";
      document.getElementById("jobPrefSkills").value = job.preferred_skills_text || "";
      document.getElementById("jobMinExp").value = job.min_experience;
      document.getElementById("jobMaxExp").value = job.max_experience;
      document.getElementById("jobEducation").value = job.education;
      document.getElementById("jobLocation").value = job.location;
    }
  } else {
    const title = document.getElementById("jobModalTitle");
    if (title) title.innerText = "Create New Job Posting";
  }

  const modal = document.getElementById("jobModal");
  if (modal) modal.classList.add("active");
}

async function handleJobSubmit(e) {
  e.preventDefault();
  if (!token) {
    showToast("Please login first to save jobs.", "error");
    openAuthModal("login");
    return;
  }

  const jobId = document.getElementById("jobIdInput").value;
  const title = document.getElementById("jobTitle").value.trim();
  const department = document.getElementById("jobDepartment").value.trim();
  const description = document.getElementById("jobDescription").value.trim();
  const reqSkillsStr = document.getElementById("jobReqSkills").value;
  const prefSkillsStr = document.getElementById("jobPrefSkills").value;
  const minExp = parseFloat(document.getElementById("jobMinExp").value) || 0;
  const maxExp = parseFloat(document.getElementById("jobMaxExp").value) || 10;
  const education = document.getElementById("jobEducation").value;
  const location = document.getElementById("jobLocation").value.trim();

  const reqSkills = reqSkillsStr.split(",").map(s => s.trim()).filter(Boolean);
  const prefSkills = prefSkillsStr.split(",").map(s => s.trim()).filter(Boolean);

  const payload = {
    title, department, description,
    required_skills: reqSkills,
    preferred_skills: prefSkills,
    min_experience: minExp,
    max_experience: maxExp,
    education, location
  };

  const method = jobId ? "PUT" : "POST";
  const url = jobId ? `${API_BASE}/jobs/${jobId}` : `${API_BASE}/jobs`;

  try {
    const res = await authFetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to save job");

    showToast(`Job "${title}" saved successfully!`);
    closeModal("jobModal");
    loadJobs();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function viewJobDetail(jobId) {
  switchView("candidates");
  const jobSelect = document.getElementById("rankingJobSelect");
  if (jobSelect) {
    jobSelect.value = jobId;
    loadCandidateRankings();
  }
}

// --- Upload & Resume Processing ---
async function loadUploadJobsDropdown() {
  if (!token || !currentUser) return;
  const select = document.getElementById("uploadJobSelect");
  if (!select) return;

  try {
    const res = await authFetch(`${API_BASE}/jobs`);
    if (res.ok) {
      currentJobs = await res.json();
      select.innerHTML = `<option value="">-- Choose Job --</option>` +
        currentJobs.map(j => `<option value="${j.id}">${j.title} (${j.department})</option>`).join("");
    }
  } catch (err) {
    console.error(err);
  }
}

function onUploadJobChange() {
  const jobId = document.getElementById("uploadJobSelect").value;
  const preview = document.getElementById("jobRequirementsPreview");
  if (!preview) return;

  if (!jobId) {
    preview.style.display = "none";
    return;
  }

  const job = currentJobs.find(j => j.id == jobId);
  if (job) {
    preview.style.display = "block";
    document.getElementById("previewJobTitle").innerText = `Job: ${job.title} (${job.location})`;
    document.getElementById("previewJobSkills").innerText = `Required Skills: ${job.required_skills_text || "General"} | Min Experience: ${job.min_experience} yrs`;
  }
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  addFilesToSelection(files);
}

const dropzone = document.getElementById("resumeDropzone");
if (dropzone) {
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const files = Array.from(e.dataTransfer.files);
    addFilesToSelection(files);
  });
}

function addFilesToSelection(files) {
  const validFiles = files.filter(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return ['pdf', 'docx', 'doc'].includes(ext);
  });

  if (validFiles.length === 0) {
    showToast("Please select valid PDF or DOCX resume files.", "error");
    return;
  }

  selectedFiles = [...selectedFiles, ...validFiles];
  renderSelectedFiles();
}

function renderSelectedFiles() {
  const container = document.getElementById("selectedFilesContainer");
  const fileList = document.getElementById("fileList");
  if (!container || !fileList) return;

  if (selectedFiles.length === 0) {
    container.style.display = "none";
    return;
  }

  container.style.display = "block";
  fileList.innerHTML = selectedFiles.map((f, i) => `
    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.04); padding: 0.5rem 0.875rem; border-radius: var(--radius-sm); border: 1px solid var(--border);">
      <div style="font-size: 0.875rem; font-weight: 600; color: #ffffff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
        <i class="bi bi-file-earmark-text text-primary me-2"></i> ${f.name} (${(f.size/1024).toFixed(1)} KB)
      </div>
      <button class="btn btn-outline btn-sm" onclick="removeSelectedFile(${i})" style="padding: 0.2rem 0.4rem; color: var(--danger); border: none;"><i class="bi bi-trash"></i></button>
    </div>
  `).join("");
}

function removeSelectedFile(index) {
  selectedFiles.splice(index, 1);
  renderSelectedFiles();
}

async function uploadAndScreenResumes() {
  const jobId = document.getElementById("uploadJobSelect").value;
  if (!jobId) {
    showToast("Please select a target job position first.", "error");
    return;
  }

  if (selectedFiles.length === 0) {
    showToast("Please select at least one resume file to upload.", "error");
    return;
  }

  if (!token) {
    showToast("Please login first to upload resumes.", "error");
    openAuthModal("login");
    return;
  }

  const formData = new FormData();
  formData.append("job_id", jobId);
  selectedFiles.forEach(f => formData.append("files", f));

  const btn = document.getElementById("btnStartScreening");
  btn.disabled = true;
  btn.innerHTML = `<i class="bi bi-hourglass-split"></i> Parsing & Evaluating Resumes...`;

  try {
    const res = await authFetch(`${API_BASE}/resumes/upload`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to process resumes");

    showToast(`Successfully screened ${data.length} candidate resume(s)!`);
    selectedFiles = [];
    renderSelectedFiles();

    switchView("candidates");
    const jobSelect = document.getElementById("rankingJobSelect");
    if (jobSelect) {
      jobSelect.value = jobId;
      loadCandidateRankings();
    }
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="bi bi-lightning-auto"></i> Start ATS Screening`;
  }
}

// --- Candidate Ranking & Filtering ---
async function loadRankingJobsDropdown() {
  if (!token || !currentUser) return;
  const select = document.getElementById("rankingJobSelect");
  if (!select) return;

  try {
    const res = await authFetch(`${API_BASE}/jobs`);
    if (res.ok) {
      currentJobs = await res.json();
      if (!currentJobs || currentJobs.length === 0) {
        select.innerHTML = `<option value="">No jobs created yet</option>`;
        const tbody = document.getElementById("candidateRankingsTbody");
        if (tbody) {
          tbody.innerHTML = `
            <tr>
              <td colspan="9">
                <div class="empty-state">
                  <div class="empty-state-icon warning"><i class="bi bi-briefcase"></i></div>
                  <h3 class="empty-state-title">No jobs created yet</h3>
                  <p class="empty-state-desc">You need to create a job position before uploading and screening candidate resumes.</p>
                  <button class="btn btn-primary" onclick="openJobModal()"><i class="bi bi-plus-lg"></i> Create New Job</button>
                </div>
              </td>
            </tr>
          `;
        }
        return;
      }

      select.innerHTML = `<option value="ALL">All Jobs (${currentJobs.length})</option>` +
        currentJobs.map(j => `<option value="${j.id}">${j.title} (${j.department})</option>`).join("");
      
      if (!select.value) {
        select.value = "ALL";
      }
      loadCandidateRankings();
    }
  } catch (err) {
    console.error(err);
  }
}

async function loadCandidateRankings() {
  if (!token || !currentUser) return;
  const jobSelect = document.getElementById("rankingJobSelect");
  if (!jobSelect) return;
  const jobId = jobSelect.value;
  const tbody = document.getElementById("candidateRankingsTbody");

  if (!jobId) {
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="empty-state">
              <div class="empty-state-icon warning"><i class="bi bi-briefcase"></i></div>
              <h3 class="empty-state-title">No jobs created yet</h3>
              <p class="empty-state-desc">Create a job opening and upload candidate resumes to start screening.</p>
              <button class="btn btn-primary" onclick="openJobModal()"><i class="bi bi-plus-lg"></i> Create New Job</button>
            </div>
          </td>
        </tr>
      `;
    }
    return;
  }

  try {
    const url = jobId === "ALL"
      ? `${API_BASE}/screening/all?status_filter=All`
      : `${API_BASE}/screening/job/${jobId}?status_filter=All`;

    const res = await authFetch(url);
    if (res.ok) {
      currentRankings = await res.json();
      filterAndSortCandidateRankings();
    }
  } catch (err) {
    console.error(err);
  }
}

function filterAndSortCandidateRankings() {
  if (!currentRankings) return;

  const searchQuery = (document.getElementById("candidateSearchInput") ? document.getElementById("candidateSearchInput").value : "").toLowerCase().trim();
  const statusFilter = document.getElementById("rankingStatusFilter") ? document.getElementById("rankingStatusFilter").value : "All";
  const sortMode = document.getElementById("candidateSortSelect") ? document.getElementById("candidateSortSelect").value : "score_desc";

  let filtered = [...currentRankings];

  // 1. Status Filter
  if (statusFilter && statusFilter.toLowerCase() !== "all") {
    filtered = filtered.filter(r => (r.status || "").toLowerCase() === statusFilter.toLowerCase());
  }

  // 2. Text Search
  if (searchQuery) {
    filtered = filtered.filter(r => {
      const name = (r.candidate_name || "").toLowerCase();
      const email = (r.candidate_email || "").toLowerCase();
      const matched = (r.matched_skills_json || "").toLowerCase();
      return name.includes(searchQuery) || email.includes(searchQuery) || matched.includes(searchQuery);
    });
  }

  // 3. Sorting
  if (sortMode === "score_desc") {
    filtered.sort((a, b) => b.overall_score - a.overall_score);
  } else if (sortMode === "score_asc") {
    filtered.sort((a, b) => a.overall_score - b.overall_score);
  } else if (sortMode === "exp_desc") {
    filtered.sort((a, b) => b.experience_score - a.experience_score);
  } else if (sortMode === "name_asc") {
    filtered.sort((a, b) => (a.candidate_name || "").localeCompare(b.candidate_name || ""));
  }

  renderCandidateRankings(filtered);
}

function renderCandidateRankings(rankings) {
  const tbody = document.getElementById("candidateRankingsTbody");
  if (!tbody) return;

  if (!rankings || rankings.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9">
          <div class="empty-state">
            <div class="empty-state-icon success"><i class="bi bi-people"></i></div>
            <h3 class="empty-state-title">No candidates yet</h3>
            <p class="empty-state-desc">No candidates found for the selected criteria. Upload candidate resumes to begin evaluation.</p>
            <button class="btn btn-primary btn-sm" onclick="switchView('upload')"><i class="bi bi-cloud-arrow-up-fill"></i> Upload Resumes</button>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = rankings.map((r, i) => {
    const matchedSkills = JSON.parse(r.matched_skills_json || "[]");
    const circularChart = renderCircularScore(r.overall_score);

    return `
      <tr>
        <td style="font-weight: 800; font-size: 1rem; color: var(--text-muted);">#${i + 1}</td>
        <td>
          <div style="font-weight: 700; color: #ffffff;">${r.candidate_name || 'Candidate'}</div>
          <div style="font-size: 0.775rem; color: var(--text-muted);">${r.candidate_email || 'N/A'}</div>
        </td>
        <td>
          ${circularChart}
        </td>
        <td><strong style="color: var(--primary);">${r.skills_score}%</strong></td>
        <td>${r.experience_score}%</td>
        <td>${r.education_score}%</td>
        <td>
          ${matchedSkills.slice(0, 3).map(s => `<span class="skill-pill matched"><i class="bi bi-check-circle-fill"></i> ${s}</span>`).join("")}
          ${matchedSkills.length > 3 ? `<span class="skill-pill">+${matchedSkills.length - 3}</span>` : ""}
        </td>
        <td>
          <select class="status-select ${r.status}" onchange="updateStatus(${r.id}, this.value)">
            <option value="Shortlisted" ${r.status === 'Shortlisted' ? 'selected' : ''}>Shortlisted</option>
            <option value="Maybe" ${r.status === 'Maybe' ? 'selected' : ''}>Maybe</option>
            <option value="Rejected" ${r.status === 'Rejected' ? 'selected' : ''}>Rejected</option>
          </select>
        </td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="viewCandidateProfile(${r.candidate_id})"><i class="bi bi-person-lines-fill"></i> View Profile</button>
        </td>
      </tr>
    `;
  }).join("");
}

async function updateStatus(screeningId, newStatus) {
  if (!token) {
    showToast("Please login to change candidate status.", "error");
    openAuthModal("login");
    return;
  }

  try {
    const res = await authFetch(`${API_BASE}/screening/${screeningId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error("Failed to update candidate status");
    showToast(`Status updated to ${newStatus}`);
    loadCandidateRankings();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- Candidate Detail Drawer / Modal ---
async function viewCandidateProfile(candidateId) {
  if (!token) {
    showToast("Authentication required.", "error");
    openAuthModal("login");
    return;
  }

  try {
    const res = await authFetch(`${API_BASE}/candidates/${candidateId}`);
    if (!res.ok) throw new Error("Failed to fetch candidate details");
    const data = await res.json();

    const cand = data.candidate;
    const history = data.screening_history[0] || {};
    const matched = JSON.parse(history.matched_skills || "[]");
    const missing = JSON.parse(history.missing_skills || "[]");
    const matchedKeywords = JSON.parse(history.job_keywords_json || "[]");

    const detectedExp = history.detected_experience || (cand.experience_years ? `${cand.experience_years} Years Experience` : "Not detected");
    const detectedEdu = history.detected_education || cand.education || "Not detected";
    const explanationText = history.explanation || history.feedback_summary || "Screening score calculated deterministically based on uploaded resume content.";

    const body = document.getElementById("candDetailBody");
    document.getElementById("candDetailName").innerText = cand.name;

    const circularScore = renderCircularScore(history.overall_score || 0);

    body.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem;">
        <div style="background: var(--surface); padding: 0.875rem; border-radius: 8px; border: 1px solid var(--border);">
          <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; margin-bottom: 0.4rem;">Contact Information</div>
          <div style="font-weight: 600; color: #ffffff; font-size: 0.875rem; margin-bottom: 0.25rem;"><i class="bi bi-envelope text-primary"></i> ${cand.email || 'Not provided'}</div>
          <div style="font-weight: 600; color: #ffffff; font-size: 0.875rem;"><i class="bi bi-telephone text-primary"></i> ${cand.phone || 'Not provided'}</div>
        </div>
        <div style="background: var(--surface); padding: 0.875rem; border-radius: 8px; border: 1px solid var(--border);">
          <div style="font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; margin-bottom: 0.4rem;">Detected Qualifications</div>
          <div style="font-weight: 600; color: #ffffff; font-size: 0.875rem; margin-bottom: 0.25rem;"><i class="bi bi-briefcase text-secondary"></i> <strong>Experience:</strong> ${detectedExp}</div>
          <div style="font-weight: 600; color: #ffffff; font-size: 0.875rem;"><i class="bi bi-mortarboard text-secondary"></i> <strong>Education:</strong> ${detectedEdu}</div>
        </div>
      </div>

      ${history.overall_score !== undefined ? `
        <div style="background: rgba(10, 14, 23, 0.7); padding: 1.25rem; border-radius: var(--radius-md); margin-bottom: 1.25rem; border: 1px solid var(--border);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-weight: 800; font-size: 1.15rem; color: #ffffff;">Overall ATS Evaluation</span>
                <span class="status-badge ${(history.status || 'maybe').toLowerCase()}">${history.status || 'Evaluated'}</span>
              </div>
              <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.2rem;">
                Target Job: <strong style="color: #ffffff;">${history.job_title || 'Target Job'}</strong> &bull; Recommendation: <strong style="color: var(--primary);">${history.recommendation || 'Evaluated Fit'}</strong>
              </div>
            </div>
            ${circularScore}
          </div>

          <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.5rem; text-align: center; font-size: 0.75rem; font-weight: 700;">
            <div style="background: var(--surface); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border);">
              <div style="color: var(--text-muted);">Skills (40%)</div>
              <div style="font-size: 1.05rem; color: var(--primary); margin-top: 0.2rem;">${history.skills_score}%</div>
            </div>
            <div style="background: var(--surface); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border);">
              <div style="color: var(--text-muted);">Exp (25%)</div>
              <div style="font-size: 1.05rem; color: var(--primary); margin-top: 0.2rem;">${history.experience_score}%</div>
            </div>
            <div style="background: var(--surface); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border);">
              <div style="color: var(--text-muted);">Edu (15%)</div>
              <div style="font-size: 1.05rem; color: var(--primary); margin-top: 0.2rem;">${history.education_score}%</div>
            </div>
            <div style="background: var(--surface); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border);">
              <div style="color: var(--text-muted);">Keywords (10%)</div>
              <div style="font-size: 1.05rem; color: var(--secondary); margin-top: 0.2rem;">${history.keyword_score}%</div>
            </div>
            <div style="background: var(--surface); padding: 0.6rem; border-radius: 8px; border: 1px solid var(--border);">
              <div style="color: var(--text-muted);">Quality (10%)</div>
              <div style="font-size: 1.05rem; color: var(--secondary); margin-top: 0.2rem;">${history.resume_quality_score}%</div>
            </div>
          </div>
        </div>

        <!-- Transparent Explanation Section -->
        <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); padding: 1rem; border-radius: var(--radius-md); margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.85rem; font-weight: 700; color: var(--primary); margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.4rem;">
            <i class="bi bi-info-circle-fill"></i> Score Transparency Breakdown & Explanation
          </h4>
          <p style="font-size: 0.825rem; line-height: 1.5; color: #e2e8f0; margin: 0;">${explanationText}</p>
        </div>

        <div style="margin-bottom: 1rem;">
          <h4 style="font-size: 0.875rem; font-weight: 700; margin-bottom: 0.5rem; color: #ffffff;">Matched Required Skills:</h4>
          <div>${matched.map(s => `<span class="skill-pill matched"><i class="bi bi-check-circle-fill"></i> ${s}</span>`).join("") || '<span style="color: var(--text-muted); font-size: 0.85rem;">None</span>'}</div>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <h4 style="font-size: 0.875rem; font-weight: 700; margin-bottom: 0.5rem; color: #ffffff;">Missing Required Skills:</h4>
          <div>${missing.map(s => `<span class="skill-pill missing"><i class="bi bi-exclamation-circle-fill"></i> ${s}</span>`).join("") || '<span style="color: var(--text-muted); font-size: 0.85rem;">None (All Required Skills Matched)</span>'}</div>
        </div>

        ${matchedKeywords && matchedKeywords.length > 0 ? `
          <div style="margin-bottom: 1.25rem;">
            <h4 style="font-size: 0.875rem; font-weight: 700; margin-bottom: 0.5rem; color: #ffffff;">Job-Relevant Keywords Matched:</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
              ${matchedKeywords.map(kw => `<span class="skill-pill" style="background: rgba(99, 102, 241, 0.15); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.3); font-size: 0.775rem;"><i class="bi bi-tag-fill me-1"></i> ${kw}</span>`).join("")}
            </div>
          </div>
        ` : ''}
      ` : ''}

      <div>
        <h4 style="font-size: 0.875rem; font-weight: 700; margin-bottom: 0.5rem; color: #ffffff;">Parsed Resume Text:</h4>
        <textarea class="form-textarea" rows="6" readonly style="font-size: 0.8rem; font-family: monospace; background: rgba(10,14,23,0.8);">${cand.raw_resume_text || 'No raw text available.'}</textarea>
      </div>
    `;

    const modal = document.getElementById("candidateDetailModal");
    if (modal) modal.classList.add("active");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// --- Reports & Analytics View Loading ---
async function loadReports() {
  if (!token || !currentUser) return;
  const container = document.getElementById("reportsContentArea");
  if (!container) return;

  try {
    const statsRes = await authFetch(`${API_BASE}/dashboard/stats`);
    const stats = statsRes.ok ? await statsRes.json() : null;

    if (!stats || stats.total_jobs === 0 || stats.screened_candidates === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon warning"><i class="bi bi-graph-up-arrow"></i></div>
          <h3 class="empty-state-title">No analytics available yet</h3>
          <p class="empty-state-desc">Create your first job position and upload candidate resumes to generate ATS screening reports and pipeline metrics.</p>
          <div style="display: flex; gap: 0.75rem; justify-content: center;">
            <button class="btn btn-primary" onclick="openJobModal()"><i class="bi bi-plus-lg"></i> Create New Job</button>
            <button class="btn btn-secondary" onclick="switchView('upload')"><i class="bi bi-cloud-upload"></i> Upload Resumes</button>
          </div>
        </div>
      `;
      return;
    }

    const scrRes = await authFetch(`${API_BASE}/screening/all?status_filter=All`);
    const allScreenings = scrRes.ok ? await scrRes.json() : [];

    const highMatch = allScreenings.filter(s => (s.overall_score || 0) >= 75).length;
    const medMatch = allScreenings.filter(s => (s.overall_score || 0) >= 50 && (s.overall_score || 0) < 75).length;
    const lowMatch = allScreenings.filter(s => (s.overall_score || 0) < 50).length;

    container.innerHTML = `
      <div class="stats-grid" style="margin-bottom: 2rem;">
        <div class="stat-card" onclick="switchView('candidates')" title="View candidate rankings">
          <div class="stat-info">
            <div class="stat-label">Average ATS Score</div>
            <div class="stat-value">${stats.average_ats_score}%</div>
          </div>
          <div class="stat-icon warning"><i class="bi bi-speedometer2"></i></div>
          <span class="card-click-hint">View Candidates <i class="bi bi-arrow-right"></i></span>
        </div>

        <div class="stat-card" onclick="navigateToCandidatesWithStatus('Shortlisted')" title="View shortlisted candidates">
          <div class="stat-info">
            <div class="stat-label">Shortlisted Candidates</div>
            <div class="stat-value">${stats.shortlisted_candidates}</div>
          </div>
          <div class="stat-icon success"><i class="bi bi-star-fill"></i></div>
          <span class="card-click-hint">Shortlisted <i class="bi bi-arrow-right"></i></span>
        </div>

        <div class="stat-card" onclick="switchView('candidates')" title="View top candidates">
          <div class="stat-info">
            <div class="stat-label">High Match (≥75%)</div>
            <div class="stat-value">${highMatch}</div>
          </div>
          <div class="stat-icon primary"><i class="bi bi-trophy-fill"></i></div>
          <span class="card-click-hint">Top Matches <i class="bi bi-arrow-right"></i></span>
        </div>

        <div class="stat-card" onclick="navigateToCandidatesWithStatus('Rejected')" title="View rejected candidates">
          <div class="stat-info">
            <div class="stat-label">Rejected Candidates</div>
            <div class="stat-value">${stats.rejected_candidates}</div>
          </div>
          <div class="stat-icon danger"><i class="bi bi-x-circle"></i></div>
          <span class="card-click-hint">Rejected <i class="bi bi-arrow-right"></i></span>
        </div>
      </div>

      <div class="card" style="margin-bottom: 2rem;">
        <div class="card-header">
          <h2 class="card-title"><i class="bi bi-bar-chart-line-fill text-primary"></i> ATS Score Distribution</h2>
        </div>
        <div style="padding: 1rem 0; display: flex; flex-direction: column; gap: 1.25rem;">
          <div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.4rem;">
              <span style="color: var(--success);"><i class="bi bi-circle-fill" style="font-size: 0.6rem;"></i> High Match (75% - 100%)</span>
              <span>${highMatch} Candidates (${stats.screened_candidates ? Math.round((highMatch/stats.screened_candidates)*100) : 0}%)</span>
            </div>
            <div style="height: 10px; background: rgba(255,255,255,0.06); border-radius: 5px; overflow: hidden;">
              <div style="height: 100%; width: ${stats.screened_candidates ? (highMatch/stats.screened_candidates)*100 : 0}%; background: var(--success); border-radius: 5px; transition: width 0.4s ease;"></div>
            </div>
          </div>

          <div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.4rem;">
              <span style="color: var(--warning);"><i class="bi bi-circle-fill" style="font-size: 0.6rem;"></i> Moderate Match (50% - 74%)</span>
              <span>${medMatch} Candidates (${stats.screened_candidates ? Math.round((medMatch/stats.screened_candidates)*100) : 0}%)</span>
            </div>
            <div style="height: 10px; background: rgba(255,255,255,0.06); border-radius: 5px; overflow: hidden;">
              <div style="height: 100%; width: ${stats.screened_candidates ? (medMatch/stats.screened_candidates)*100 : 0}%; background: var(--warning); border-radius: 5px; transition: width 0.4s ease;"></div>
            </div>
          </div>

          <div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 700; margin-bottom: 0.4rem;">
              <span style="color: var(--danger);"><i class="bi bi-circle-fill" style="font-size: 0.6rem;"></i> Low Match (&lt;50%)</span>
              <span>${lowMatch} Candidates (${stats.screened_candidates ? Math.round((lowMatch/stats.screened_candidates)*100) : 0}%)</span>
            </div>
            <div style="height: 10px; background: rgba(255,255,255,0.06); border-radius: 5px; overflow: hidden;">
              <div style="height: 100%; width: ${stats.screened_candidates ? (lowMatch/stats.screened_candidates)*100 : 0}%; background: var(--danger); border-radius: 5px; transition: width 0.4s ease;"></div>
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error("Reports error:", err);
  }
}

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
  setupQuickActions();

  const path = window.location.pathname;

  if (token && currentUser) {
    if (path.includes("/jobs/create")) {
      switchView("jobs");
      setTimeout(openJobModal, 100);
    } else if (path.includes("/resumes/upload") || path.includes("/upload")) {
      switchView("upload");
    } else if (path.includes("/candidates")) {
      switchView("candidates");
    } else if (path.includes("/reports")) {
      switchView("reports");
    } else if (path.includes("/jobs")) {
      switchView("jobs");
    } else {
      switchView("dashboard");
    }
  } else {
    resetViewData();
    document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
    const pubSec = document.getElementById("view-public");
    if (pubSec) pubSec.classList.add("active");

    if (path.includes("dashboard") || path.includes("jobs") || path.includes("candidates") || path.includes("upload") || path.includes("reports")) {
      showToast("Please sign in to access this page.", "error");
      openAuthModal("login");
    }
  }
});

// Popstate navigation listener for browser forward/back buttons
window.addEventListener("popstate", () => {
  const path = window.location.pathname;
  if (!token || !currentUser) return;
  if (path.includes("/jobs/create")) {
    switchView("jobs");
    openJobModal();
  } else if (path.includes("/upload")) {
    switchView("upload");
  } else if (path.includes("/candidates")) {
    switchView("candidates");
  } else if (path.includes("/reports")) {
    switchView("reports");
  } else if (path.includes("/jobs")) {
    switchView("jobs");
  } else {
    switchView("dashboard");
  }
});

// Explicitly bind all public interactive functions to window
window.handleQuickAction = handleQuickAction;
window.setupQuickActions = setupQuickActions;
window.scrollToQuickActions = scrollToQuickActions;
window.switchView = switchView;
window.openJobModal = openJobModal;
window.closeModal = closeModal;
window.viewCandidateProfile = viewCandidateProfile;
window.loadDashboard = loadDashboard;
window.renderDashboardCandidates = renderDashboardCandidates;
window.renderDashboardJobs = renderDashboardJobs;
window.viewJobDetail = viewJobDetail;
window.openAuthModal = openAuthModal;
window.toggleAuthTab = toggleAuthTab;
window.logout = logout;
window.updateStatus = updateStatus;
window.loadCandidateRankings = loadCandidateRankings;
window.filterAndSortCandidateRankings = filterAndSortCandidateRankings;

