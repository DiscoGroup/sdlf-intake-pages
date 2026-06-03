const config = window.INTAKE_CONFIG;
const form = document.querySelector("#claim-form");
const steps = config.steps;
const stepCount = document.querySelector("#stepCount");
const progressBar = document.querySelector("#progressBar");
const stepMount = document.querySelector("#stepMount");
const backButton = document.querySelector("#backButton");
const nextButton = document.querySelector("#nextButton");
const submitButton = document.querySelector("#submitButton");
const resultBox = document.querySelector("#resultBox");
const resultTitle = document.querySelector("#resultTitle");
const resultDetail = document.querySelector("#resultDetail");
const formStatus = document.querySelector("#formStatus");
const isStaticPreview = location.hostname.endsWith("github.io");

if (isStaticPreview) {
  document.body.classList.add("preview-mode");
}

const state = {
  step: 0,
  values: {
    bestTime: "Any time",
    medicalBills: 0,
    lostWages: 0,
    propertyDamage: 0
  },
  labels: {}
};

function setAnswer(name, value, label, score = 0, map = {}) {
  state.values[name] = value;
  state.labels[name] = label;
  state.values[`${name}Score`] = score;
  Object.assign(state.values, map);
}

function collectInputs() {
  const data = new FormData(form);
  for (const [key, value] of data.entries()) {
    state.values[key] = value;
  }
}

function choiceStep(step) {
  const buttons = step.options.map((option) => {
    const selected = state.values[step.name] === option.value ? " is-selected" : "";
    return `<button class="${selected}" type="button" data-value="${escapeHtml(option.value)}" data-label="${escapeHtml(option.label)}" data-score="${option.score || 0}" data-map='${escapeHtml(JSON.stringify(option.map || {}))}'>${escapeHtml(option.label)}</button>`;
  }).join("");

  return `
    <h2>${escapeHtml(step.title)}</h2>
    ${step.note ? `<p class="step-note">${escapeHtml(step.note)}</p>` : ""}
    <div class="choice-list" data-name="${escapeHtml(step.name)}">${buttons}</div>
  `;
}

function fieldsStep(step) {
  const fields = step.fields.map((field) => {
    if (field.type === "textarea") {
      return `
        <label class="field-label">
          ${escapeHtml(field.label)}
          <textarea name="${escapeHtml(field.name)}" rows="${field.rows || 5}" maxlength="${field.maxlength || 1600}" ${field.required ? "required" : ""} placeholder="${escapeHtml(field.placeholder || "")}">${escapeHtml(state.values[field.name] || "")}</textarea>
        </label>
      `;
    }

    if (field.type === "select") {
      const options = field.options.map((option) => {
        const selected = (state.values[field.name] || field.value || "") === option ? " selected" : "";
        return `<option${selected}>${escapeHtml(option)}</option>`;
      }).join("");
      return `
        <label class="field-label">
          ${escapeHtml(field.label)}
          <select name="${escapeHtml(field.name)}" ${field.required ? "required" : ""}>${options}</select>
        </label>
      `;
    }

    return `
      <label class="field-label">
        ${escapeHtml(field.label)}
        <input name="${escapeHtml(field.name)}" type="${escapeHtml(field.type || "text")}" value="${escapeHtml(state.values[field.name] || "")}" ${field.required ? "required" : ""} autocomplete="${escapeHtml(field.autocomplete || "")}" placeholder="${escapeHtml(field.placeholder || "")}">
      </label>
    `;
  }).join("");

  return `
    <h2>${escapeHtml(step.title)}</h2>
    ${step.note ? `<p class="step-note">${escapeHtml(step.note)}</p>` : ""}
    <div class="field-grid">${fields}</div>
  `;
}

function finalStep(step) {
  return `
    <h2>${escapeHtml(step.title)}</h2>
    ${step.note ? `<p class="step-note">${escapeHtml(step.note)}</p>` : ""}
    <label class="field-label">
      Full name
      <input name="fullName" type="text" autocomplete="name" required placeholder="Jane Doe" value="${escapeHtml(state.values.fullName || "")}">
    </label>
    <label class="field-label">
      Email
      <input name="email" type="email" autocomplete="email" required placeholder="jane@example.com" value="${escapeHtml(state.values.email || "")}">
    </label>
    <label class="field-label">
      Phone
      <input name="phone" type="tel" autocomplete="tel" required placeholder="(555) 555-5555" value="${escapeHtml(state.values.phone || "")}">
    </label>
    <label class="consent">
      <input name="consent" type="checkbox" required ${state.values.consent ? "checked" : ""}>
      <span>${escapeHtml(config.consent)}</span>
    </label>
  `;
}

function renderStep() {
  collectInputs();
  const step = steps[state.step];
  stepMount.className = "wizard-step is-active";
  if (step.type === "choice") {
    stepMount.innerHTML = choiceStep(step);
  } else if (step.type === "final") {
    stepMount.innerHTML = finalStep(step);
  } else {
    stepMount.innerHTML = fieldsStep(step);
  }

  stepCount.textContent = `${state.step + 1} of ${steps.length}`;
  progressBar.style.width = `${((state.step + 1) / steps.length) * 100}%`;
  backButton.style.visibility = state.step === 0 ? "hidden" : "visible";
  nextButton.hidden = state.step === steps.length - 1;
  submitButton.hidden = state.step !== steps.length - 1;
  formStatus.textContent = "";
  formStatus.classList.remove("error");
  renderQualification();
}

function scoreLead() {
  collectInputs();
  const points = Object.entries(state.values)
    .filter(([key]) => key.endsWith("Score"))
    .reduce((total, [, value]) => total + Number(value || 0), 0);
  const adjusted = Math.max(0, Math.min(100, points));
  const status = adjusted >= config.thresholds.strong
    ? "Strong lead"
    : adjusted >= config.thresholds.review
      ? "Needs review"
      : "Weak lead";
  return { score: adjusted, status };
}

function renderQualification() {
  const { score, status } = scoreLead();
  resultTitle.textContent = status;
  resultDetail.textContent = `${score}/100 qualification score. ${config.resultHint}`;
  resultBox.hidden = state.step < steps.length - 1;
}

function validateStep() {
  collectInputs();
  const step = steps[state.step];
  if (step.type === "choice" && !state.values[step.name]) {
    return "Please choose an option.";
  }

  const required = Array.from(stepMount.querySelectorAll("[required]"));
  for (const field of required) {
    if (field.type === "checkbox" && !field.checked) {
      return "Please confirm consent to be contacted.";
    }
    if (field.type !== "checkbox" && !field.value.trim()) {
      return "Please complete the required fields.";
    }
  }
  return "";
}

function qualificationSummary() {
  return config.steps
    .filter((step) => state.labels[step.name] || state.values[step.name])
    .map((step) => `${step.title}: ${state.labels[step.name] || state.values[step.name]}`)
    .join(" | ");
}

function submissionPayload() {
  collectInputs();
  const { score, status } = scoreLead();
  const summaryParts = [
    state.values.caseSummary,
    state.values.exposureSummary,
    state.values.workplaceSummary,
    state.values.detentionSummary
  ].filter(Boolean);

  return {
    caseCategory: config.category,
    leadStatus: status,
    leadScore: score,
    qualificationSummary: qualificationSummary(),
    fullName: state.values.fullName || "",
    phone: state.values.phone || "",
    email: state.values.email || "",
    injuryType: state.values.injuryType || config.category,
    injured: state.values.injured || "",
    accidentDate: state.values.accidentDate || state.values.diagnosisDate || state.values.lastIncident || "",
    medicalBills: state.values.medicalBills || 0,
    lostWages: state.values.lostWages || 0,
    propertyDamage: state.values.propertyDamage || 0,
    fault: state.values.fault || "",
    treatment: state.values.treatment || state.values.diagnosis || "",
    bestTime: state.values.bestTime || "Any time",
    estimateLow: 0,
    estimateHigh: 0,
    caseSummary: summaryParts.join("\n\n"),
    qualificationData: {
      answers: state.values,
      labels: state.labels
    },
    page: window.location.href
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

stepMount.addEventListener("click", (event) => {
  const button = event.target.closest(".choice-list button");
  if (!button) {
    return;
  }
  const list = button.closest(".choice-list");
  const map = JSON.parse(button.dataset.map || "{}");
  setAnswer(list.dataset.name, button.dataset.value, button.dataset.label, Number(button.dataset.score || 0), map);
  renderStep();
  window.setTimeout(() => {
    if (state.step < steps.length - 1) {
      state.step += 1;
      renderStep();
    }
  }, 120);
});

form.addEventListener("input", renderQualification);
form.addEventListener("change", renderQualification);

backButton.addEventListener("click", () => {
  state.step -= 1;
  renderStep();
});

nextButton.addEventListener("click", () => {
  const error = validateStep();
  if (error) {
    formStatus.classList.add("error");
    formStatus.textContent = error;
    return;
  }
  state.step += 1;
  renderStep();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const error = validateStep();
  if (error) {
    formStatus.classList.add("error");
    formStatus.textContent = error;
    return;
  }

  formStatus.classList.remove("error");

  if (isStaticPreview) {
    const { score, status } = scoreLead();
    formStatus.textContent = `Beta preview complete: ${status} (${score}/100). Render backend will save and email this lead after deployment.`;
    form.querySelectorAll("button, input, textarea, select").forEach((element) => {
      element.disabled = true;
    });
    return;
  }

  formStatus.textContent = "Saving your review...";

  try {
    const response = await fetch("/api/submissions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submissionPayload())
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Submission failed");
    }
    formStatus.textContent = result.emailSent
      ? "Thank you. Your submission was saved and emailed for review."
      : "Thank you. Your submission was saved. Email export is pending SMTP configuration.";
    form.querySelectorAll("button, input, textarea, select").forEach((element) => {
      element.disabled = true;
    });
  } catch (error) {
    formStatus.classList.add("error");
    formStatus.textContent = error.message;
  }
});

renderStep();
