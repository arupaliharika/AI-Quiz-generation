const state = {
  token: null,
  user: null,
  contentId: null,
  questions: [],
  currentIndex: 0,
  selectedOption: null,
  answered: 0,
  correct: 0,
  startedAt: null,
};

const qs = (id) => document.getElementById(id);

const authStatus = qs("auth-status");
const authEmail = qs("auth-email");
const authPassword = qs("auth-password");
let isRegister = false;

const difficultyPill = qs("difficulty-pill");
const difficultySummary = qs("difficulty-pill-summary");
const accuracyPill = qs("accuracy-pill");
const attemptsPill = qs("attempts-pill");

const summaryScore = qs("summary-score");
const summaryCorrect = qs("summary-correct");
const summaryTotal = qs("summary-total");

const typePills = qs("type-pills");
const questionText = qs("question-text");
const optionsContainer = qs("options");
const quizProgress = qs("quiz-progress");
const answerStatus = qs("answer-status");
const answerFeedback = qs("answer-feedback");
const quizTrackFill = qs("quiz-track-fill");
const viewResultsBtn = qs("view-results");
const nextAnalysisBtn = qs("next-analysis");
const logoutBtn = qs("logout-btn");
const openAuthBtn = qs("open-auth");
const openRegisterBtn = qs("open-register");

function setStatus(el, message, tone) {
  if (!el) return;
  el.textContent = message;
  el.style.color = tone === "error" ? "#b3261e" : "#5f5c66";
}

function updateSummary() {
  summaryCorrect.textContent = state.correct.toString();
  summaryTotal.textContent = state.answered.toString();
  const accuracy = state.answered
    ? Math.round((state.correct / state.answered) * 100)
    : 0;
  summaryScore.textContent = `${accuracy}%`;
  accuracyPill.textContent = state.answered ? `${accuracy}%` : "--";
  attemptsPill.textContent = state.answered ? state.answered : "--";
  if (difficultySummary) {
    difficultySummary.textContent = difficultyPill.textContent;
  }
}

function showPage(pageId) {
  document.querySelectorAll(".page").forEach((page) => {
    page.classList.remove("active");
  });
  const page = document.getElementById(`page-${pageId}`);
  if (page) page.classList.add("active");

  document.querySelectorAll("#main-nav a").forEach((link) => {
    link.classList.toggle("active", link.dataset.page === pageId);
  });
}

function setAuthMode(registerMode) {
  isRegister = registerMode;
  authStatus.textContent = "";
  document.getElementById("auth-login-tab").classList.toggle("active", !registerMode);
  document.getElementById("auth-signup-tab").classList.toggle("active", registerMode);
}

function setAuthUI(loggedIn) {
  if (!logoutBtn || !openAuthBtn || !openRegisterBtn) return;
  logoutBtn.classList.toggle("hidden", !loggedIn);
  openAuthBtn.classList.toggle("hidden", loggedIn);
  openRegisterBtn.classList.toggle("hidden", loggedIn);
}

async function api(path, options = {}, allowRetry = true) {
  const headers = options.headers || {};
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...headers },
  });

  if (allowRetry && (response.status === 401 || response.status === 422)) {
    state.token = null;
    return api(path, options, false);
  }

  let data = null;
  let text = "";
  try {
    data = await response.json();
  } catch (err) {
    text = await response.text().catch(() => "");
  }
  if (!response.ok) {
    const message =
      (data && data.error) ||
      text ||
      `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data || {};
}

function renderQuestion() {
  const total = state.questions.length;
  quizProgress.textContent = `${Math.min(state.currentIndex + 1, total)} / ${total}`;
  if (quizTrackFill && total > 0) {
    quizTrackFill.style.width = `${((state.currentIndex + 1) / total) * 100}%`;
  }

  const current = state.questions[state.currentIndex];
  if (!current) {
    questionText.textContent = "No questions yet.";
    optionsContainer.innerHTML = "";
    if (answerFeedback) answerFeedback.textContent = "";
    if (viewResultsBtn) viewResultsBtn.classList.add("hidden");
    return;
  }
  questionText.textContent = current.question;
  optionsContainer.innerHTML = "";
  state.selectedOption = null;
  if (answerFeedback) answerFeedback.textContent = "";
  if (answerStatus) answerStatus.textContent = "";
  if (viewResultsBtn) viewResultsBtn.classList.add("hidden");

  const options = current.options && current.options.length
    ? current.options
    : ["True", "False"].includes(current.answer)
    ? ["True", "False"]
    : ["Type answer", current.answer];

  const selectOption = (buttonEl) => {
    document.querySelectorAll(".option").forEach((el) => {
      el.classList.remove("selected");
    });
    buttonEl.classList.add("selected");
    state.selectedOption = buttonEl.dataset.option || buttonEl.textContent;
  };

  options.forEach((option) => {
    const btn = document.createElement("button");
    btn.className = "option";
    btn.type = "button";
    btn.textContent = option;
    btn.dataset.option = option;
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      selectOption(btn);
    });
    btn.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectOption(btn);
      }
    });
    optionsContainer.appendChild(btn);
  });
}

optionsContainer.addEventListener("click", (event) => {
  const target = event.target.closest(".option");
  if (!target) return;
  event.preventDefault();
  document.querySelectorAll(".option").forEach((el) => {
    el.classList.remove("selected");
  });
  target.classList.add("selected");
  state.selectedOption = target.dataset.option || target.textContent;
});

optionsContainer.addEventListener("pointerdown", (event) => {
  const target = event.target.closest(".option");
  if (!target) return;
  event.preventDefault();
  document.querySelectorAll(".option").forEach((el) => {
    el.classList.remove("selected");
  });
  target.classList.add("selected");
  state.selectedOption = target.dataset.option || target.textContent;
});

async function refreshAdmin() {
  try {
    const data = await api("/api/admin/overview");
    const grid = qs("admin-grid");
    const values = [data.users, data.content_items, data.questions, data.attempts];
    grid.querySelectorAll("h4").forEach((el, idx) => {
      el.textContent = values[idx];
    });
  } catch (err) {
    setStatus(qs("quiz-status"), "Admin overview unavailable.", "error");
  }
}

function normalizeDifficulty(label) {
  return label ? label[0].toUpperCase() + label.slice(1) : "Adaptive";
}

openAuthBtn.onclick = () => {
  showPage("auth");
  setAuthMode(false);
};
openRegisterBtn.onclick = () => {
  showPage("auth");
  setAuthMode(true);
};
document.getElementById("auth-login-tab").onclick = () => setAuthMode(false);
document.getElementById("auth-signup-tab").onclick = () => setAuthMode(true);

document.querySelectorAll("#main-nav a").forEach((link) => {
  link.onclick = (event) => {
    event.preventDefault();
    const page = link.dataset.page;
    if (page) showPage(page);
  };
});

document.getElementById("submit-auth").onclick = async () => {
  const email = authEmail.value.trim();
  const password = authPassword.value.trim();
  if (!email || !password) {
    setStatus(authStatus, "Email and password are required.", "error");
    return;
  }
  try {
    const payload = { email, password };
    if (isRegister) {
      payload.difficulty_pref = "medium";
    }
    const data = await api(isRegister ? "/api/auth/register" : "/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.token = data.token;
    state.user = data.user;
    setStatus(qs("content-status"), `Welcome, ${state.user.email}.`);
    setAuthUI(true);
    showPage("setup");
  } catch (err) {
    setStatus(authStatus, err.message, "error");
  }
};

document.getElementById("save-content").onclick = async () => {
  const title = qs("content-title").value.trim();
  const text = qs("content-text").value.trim();
  const fileInput = qs("content-file");
  const file = fileInput && fileInput.files ? fileInput.files[0] : null;
  if (file && file.type === "application/pdf") {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title || file.name.replace(/\.[^.]+$/, ""));
    try {
      const response = await fetch("/api/content/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `Request failed (${response.status})`);
      }
      state.contentId = data.id;
      if (data.token) {
        state.token = data.token;
        state.user = data.user;
      }
      setStatus(qs("content-status"), "PDF uploaded and parsed.");
    } catch (err) {
      setStatus(qs("content-status"), err.message, "error");
    }
    return;
  }
  if (text.length < 20) {
    setStatus(qs("content-status"), "Please add at least 20 characters.", "error");
    return;
  }
  try {
    const data = await api("/api/content", {
      method: "POST",
      body: JSON.stringify({ title, text }),
    });
    state.contentId = data.id;
    if (data.token) {
      state.token = data.token;
      state.user = data.user;
    }
    setStatus(qs("content-status"), "Content saved. Ready to generate quiz.");
  } catch (err) {
    setStatus(qs("content-status"), err.message, "error");
  }
};

document.getElementById("content-file").onchange = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const status = qs("content-status");
  if (file.type === "application/pdf") {
    setStatus(status, "PDF selected. Click Save Content to extract text.");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    const text = reader.result ? reader.result.toString() : "";
    qs("content-text").value = text;
    if (!qs("content-title").value.trim()) {
      qs("content-title").value = file.name.replace(/\.[^.]+$/, "");
    }
    setStatus(status, "File loaded into the editor.");
  };
  reader.onerror = () => {
    setStatus(status, "Unable to read the file.", "error");
  };
  reader.readAsText(file);
};

typePills.addEventListener("click", (event) => {
  if (!event.target.matches(".pill")) return;
  event.target.classList.toggle("active");
});

document.getElementById("generate-quiz").onclick = async () => {
  if (!state.contentId) {
    setStatus(qs("quiz-status"), "Please save content first.", "error");
    return;
  }
  const types = Array.from(typePills.querySelectorAll(".pill.active")).map(
    (pill) => pill.dataset.type
  );
  const difficulty = qs("difficulty-select").value || null;
  const numQuestions = qs("count-select").value;
  try {
    const data = await api("/api/quiz/generate", {
      method: "POST",
      body: JSON.stringify({
        content_id: state.contentId,
        types,
        difficulty,
        num_questions: numQuestions,
      }),
    });
    state.questions = data;
    state.currentIndex = 0;
    setStatus(qs("quiz-status"), `Generated ${data.length} questions.`);
    renderQuestion();
    showPage("quiz");
  } catch (err) {
    setStatus(qs("quiz-status"), err.message, "error");
  }
};

const startQuizBtn = document.getElementById("start-quiz");
if (startQuizBtn) {
  startQuizBtn.onclick = async () => {
    if (!state.token) {
      showPage("auth");
      return;
    }
    try {
      const data = await api("/api/quiz/next");
      state.questions = [data];
      state.currentIndex = 0;
      state.startedAt = Date.now();
      difficultyPill.textContent = normalizeDifficulty(data.suggested_difficulty);
      if (difficultySummary) {
        difficultySummary.textContent = difficultyPill.textContent;
      }
      renderQuestion();
      showPage("quiz");
    } catch (err) {
      setStatus(answerStatus, err.message, "error");
    }
  };
}

document.getElementById("skip-question").onclick = () => {
  if (!state.questions.length) return;
  state.currentIndex = (state.currentIndex + 1) % state.questions.length;
  renderQuestion();
};

document.getElementById("submit-answer").onclick = async () => {
  const current = state.questions[state.currentIndex];
  if (!state.selectedOption) {
    const selected = document.querySelector(".option.selected");
    if (selected) state.selectedOption = selected.dataset.option || selected.textContent;
  }
  if (!current || !state.selectedOption) {
    setStatus(answerStatus, "Select an option to continue.", "error");
    return;
  }
  const isCorrect = state.selectedOption === current.answer;
  state.answered += 1;
  if (isCorrect) state.correct += 1;
  updateSummary();
  setStatus(
    answerStatus,
    `${isCorrect ? "Correct." : "Incorrect."} Answer: ${current.answer}.`,
    isCorrect ? "ok" : "error"
  );

  if (state.token && current.id) {
    const responseTimeMs = state.startedAt ? Date.now() - state.startedAt : 0;
    await api("/api/attempt", {
      method: "POST",
      body: JSON.stringify({
        question_id: current.id,
        is_correct: isCorrect,
        response_time_ms: responseTimeMs,
      }),
    }).catch(() => {});
    state.startedAt = Date.now();
  }

  const optionButtons = Array.from(document.querySelectorAll(".option"));
  optionButtons.forEach((btn) => {
    if (btn.textContent === current.answer) {
      btn.classList.add("correct");
    }
    if (!isCorrect && btn.textContent === state.selectedOption) {
      btn.classList.add("wrong");
    }
  });

  if (answerFeedback) {
    const source = current.source || "";
    const trimmed = source.length > 220 ? `${source.slice(0, 217)}...` : source;
    answerFeedback.textContent = trimmed
      ? `Explanation: ${trimmed}`
      : "Explanation: The correct option is taken from your uploaded material.";
  }

  const lastIndex = state.questions.length - 1;
  if (state.currentIndex >= lastIndex) {
    if (viewResultsBtn) viewResultsBtn.classList.remove("hidden");
    return;
  }
  setTimeout(() => {
    state.currentIndex += 1;
    renderQuestion();
  }, 900);
};

updateSummary();
refreshAdmin();
setAuthMode(false);
showPage("auth");
setAuthUI(false);

if (logoutBtn) {
  logoutBtn.onclick = () => {
    state.token = null;
    state.user = null;
    setAuthUI(false);
    showPage("auth");
  };
}

if (viewResultsBtn) {
  viewResultsBtn.onclick = () => {
    updateSummary();
    showPage("dashboard");
  };
}

if (nextAnalysisBtn) {
  nextAnalysisBtn.onclick = () => {
    updateSummary();
    showPage("analysis");
  };
}
