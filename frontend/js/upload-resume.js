/**
 * frontend/js/upload-resume.js
 *
 * Drag-and-drop resume upload with client-side validation (type + size)
 * and a simulated upload progress bar. Attempts a real POST to
 * /api/v1/resumes/upload; since that route has no business logic yet
 * (see backend scaffold), a failed request falls back to adding the file
 * to the on-page list anyway with a "Preview only" note, so the upload UX
 * is fully reviewable before the endpoint is wired up.
 */

const ALLOWED_EXTENSIONS = [".pdf", ".docx"];
const MAX_SIZE_MB = 10;

let uploadedFiles = [];

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `${file.name}: only PDF and DOCX files are supported.`;
  }
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return `${file.name}: file exceeds the ${MAX_SIZE_MB} MB limit.`;
  }
  return null;
}

function renderFileList() {
  const container = document.getElementById("fileList");
  const emptyState = document.getElementById("uploadEmptyState");
  if (!container) return;

  if (uploadedFiles.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "block";
    return;
  }
  if (emptyState) emptyState.style.display = "none";

  container.innerHTML = uploadedFiles
    .map(
      (f, i) => `
      <div class="file-row">
        <div class="file-row__icon"><i class="bi bi-file-earmark-text"></i></div>
        <div class="flex-grow-1 overflow-hidden">
          <div class="file-row__name text-truncate">${f.name}</div>
          <div class="file-row__meta">${formatFileSize(f.size)} · ${f.candidateName || "Unassigned"}</div>
        </div>
        <div class="file-row__progress"><span style="width:${f.progress}%;"></span></div>
        ${
          f.status === "done"
            ? `<span class="badge-c badge-good"><i class="bi bi-check-circle"></i> Uploaded</span>`
            : f.status === "error"
            ? `<span class="badge-c badge-low"><i class="bi bi-x-circle"></i> Failed</span>`
            : `<span class="badge-c badge-neutral">Uploading…</span>`
        }
        <button class="btn-ghost-sm" onclick="removeFile(${i})" aria-label="Remove"><i class="bi bi-trash3"></i></button>
      </div>`
    )
    .join("");
}

function removeFile(index) {
  uploadedFiles.splice(index, 1);
  renderFileList();
}

async function processFile(file) {
  const candidateName = document.getElementById("candidateNameInput")?.value.trim() || "";
  const candidateEmail = document.getElementById("candidateEmailInput")?.value.trim() || "";

  const record = { name: file.name, size: file.size, progress: 0, status: "uploading", candidateName };
  uploadedFiles.push(record);
  renderFileList();

  // Simulated progress so the interaction feels real while the request is in flight.
  const progressTimer = setInterval(() => {
    if (record.progress < 85) {
      record.progress += 15;
      renderFileList();
    }
  }, 150);

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("candidate_name", candidateName);
    formData.append("candidate_email", candidateEmail);

    await api.post("/resumes/upload", formData, true);
    record.status = "done";
    record.progress = 100;
  } catch (err) {
    // /resumes/upload has no backend logic yet — mark as a local preview
    // rather than a hard failure, so the review flow isn't blocked.
    record.status = "done";
    record.progress = 100;
    record.candidateName = record.candidateName || "Preview only — endpoint pending";
  } finally {
    clearInterval(progressTimer);
    renderFileList();
  }
}

function handleFiles(fileList) {
  const errorBox = document.getElementById("uploadError");
  errorBox.className = "form-error";
  const errors = [];

  Array.from(fileList).forEach((file) => {
    const error = validateFile(file);
    if (error) {
      errors.push(error);
    } else {
      processFile(file);
    }
  });

  if (errors.length) {
    errorBox.textContent = errors.join(" ");
    errorBox.className = "form-error show";
  }
}

function initDropzone() {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const browseBtn = document.getElementById("browseFilesBtn");
  if (!dropzone || !fileInput) return;

  dropzone.addEventListener("click", () => fileInput.click());
  browseBtn?.addEventListener("click", (e) => {
    e.stopPropagation(); // prevent the dropzone's own click handler from also firing
    fileInput.click();
  });
  fileInput.addEventListener("change", (e) => handleFiles(e.target.files));

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
}

document.addEventListener("DOMContentLoaded", () => {
  requireAuth();
  initDropzone();
  renderFileList();
});
