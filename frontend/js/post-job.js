/**
 * frontend/js/post-job.js
 *
 * Handles the "Post Job" form, including a custom skill tag input
 * (type + Enter/comma to add, click x to remove). Attempts a real POST
 * to /api/v1/jobs/; that route has no business logic yet, so on failure
 * the form still shows a success state locally (clearly noted) rather
 * than blocking the review of the UI.
 */

let skills = [];

function renderTags() {
  const container = document.getElementById("tagChips");
  container.innerHTML = skills
    .map(
      (skill, i) => `
      <span class="tag-chip">
        ${skill}
        <button type="button" onclick="removeSkill(${i})" aria-label="Remove ${skill}"><i class="bi bi-x-lg" style="font-size:0.65rem;"></i></button>
      </span>`
    )
    .join("");
}

function removeSkill(index) {
  skills.splice(index, 1);
  renderTags();
}

function addSkillFromInput(input) {
  const value = input.value.trim().replace(/,$/, "");
  if (value && !skills.includes(value)) {
    skills.push(value);
    renderTags();
  }
  input.value = "";
}

function initTagInput() {
  const input = document.getElementById("skillInput");
  if (!input) return;

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkillFromInput(input);
    } else if (e.key === "Backspace" && input.value === "" && skills.length) {
      skills.pop();
      renderTags();
    }
  });
  input.addEventListener("blur", () => addSkillFromInput(input));
}

function showFormAlert(message, type) {
  const el = document.getElementById("jobFormAlert");
  el.textContent = message;
  el.className = `auth-alert show ${type}`;
}

function initJobForm() {
  const form = document.getElementById("postJobForm");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("jobTitle").value.trim();
    const department = document.getElementById("jobDepartment").value.trim();
    const description = document.getElementById("jobDescription").value.trim();
    const minExperience = document.getElementById("jobMinExperience").value;
    const education = document.getElementById("jobEducation").value.trim();

    if (!title || !description) {
      showFormAlert("Job title and description are required.", "error");
      return;
    }
    if (skills.length === 0) {
      showFormAlert("Add at least one required skill.", "error");
      return;
    }

    const submitBtn = document.getElementById("postJobSubmitBtn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner-c me-2"></span>Publishing…`;

    const payload = {
      title,
      department,
      description,
      min_experience_years: minExperience ? Number(minExperience) : null,
      required_education: education || null,
      skills,
    };

    try {
      await api.post("/jobs/", payload);
      showFormAlert("Job posted successfully. Redirecting to results…", "success");
    } catch (err) {
      // /jobs/ has no backend logic yet — treat as a local preview success
      // rather than blocking the form, matching the pattern used on the
      // resume upload page.
      showFormAlert("Job saved as preview (screening endpoint not yet connected).", "success");
    }

    setTimeout(() => (window.location.href = "results.html"), 1300);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  initTagInput();
  initJobForm();
});
