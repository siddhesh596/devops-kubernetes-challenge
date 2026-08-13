/**
 * script.js
 * DevOps Task Manager frontend - vanilla JS, Fetch API only.
 *
 * Matches the real backend contract:
 *  - GET /tasks returns a flat JSON array (no wrapper object), so counts
 *    are computed here on the client.
 *  - Statuses are: pending | in-progress | completed.
 *  - PUT /tasks/<id> requires a full payload (title is mandatory even
 *    when only the status is changing), so status changes always send
 *    the task's current title + description along with the new status.
 */

const API = {
  health: "/health",
  dbHealth: "/db-health",
  tasks: "/tasks",
};

const STATUSES = ["pending", "in-progress", "completed"];

const el = {
  backendStatus: document.getElementById("backend-status"),
  dbStatus: document.getElementById("db-status"),
  statTotal: document.getElementById("stat-total"),
  statPending: document.getElementById("stat-pending"),
  statInProgress: document.getElementById("stat-inprogress"),
  statCompleted: document.getElementById("stat-completed"),
  taskList: document.getElementById("task-list"),
  emptyState: document.getElementById("empty-state"),
  addForm: document.getElementById("add-task-form"),
  titleInput: document.getElementById("task-title"),
  descriptionInput: document.getElementById("task-description"),
  formError: document.getElementById("form-error"),
  refreshBtn: document.getElementById("refresh-btn"),
};

function setStatus(pillEl, ok, label) {
  pillEl.classList.remove("status-ok", "status-bad", "status-unknown");
  pillEl.classList.add(ok ? "status-ok" : "status-bad");
  pillEl.textContent = label;
}

async function checkBackendHealth() {
  try {
    const res = await fetch(API.health);
    if (!res.ok) throw new Error("bad status");
    setStatus(el.backendStatus, true, "Backend: Healthy");
  } catch (err) {
    setStatus(el.backendStatus, false, "Backend: Unhealthy");
  }
}

async function checkDbHealth() {
  try {
    const res = await fetch(API.dbHealth);
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.database === "connected") {
      setStatus(el.dbStatus, true, "Database: Connected");
    } else {
      setStatus(el.dbStatus, false, "Database: Disconnected");
    }
  } catch (err) {
    setStatus(el.dbStatus, false, "Database: Disconnected");
  }
}

function renderCounts(tasks) {
  const counts = { total: tasks.length, pending: 0, "in-progress": 0, completed: 0 };
  tasks.forEach((t) => {
    if (counts[t.status] !== undefined) counts[t.status] += 1;
  });
  el.statTotal.textContent = counts.total;
  el.statPending.textContent = counts.pending;
  el.statInProgress.textContent = counts["in-progress"];
  el.statCompleted.textContent = counts.completed;
}

function badgeClass(status) {
  if (status === "completed") return "badge-completed";
  if (status === "in-progress") return "badge-in-progress";
  return "badge-pending";
}

function statusOptions(current) {
  return STATUSES.map(
    (s) => `<option value="${s}" ${s === current ? "selected" : ""}>${s}</option>`
  ).join("");
}

function taskRow(task) {
  const row = document.createElement("div");
  row.className = "task-row";

  const isCompleted = task.status === "completed";

  row.innerHTML = `
    <span class="task-id">#${task.id}</span>
    <div class="task-body">
      <p class="task-title ${isCompleted ? "completed" : ""}">${escapeHtml(task.title)}</p>
      ${task.description ? `<p class="task-description">${escapeHtml(task.description)}</p>` : ""}
      <div class="task-meta">
        <span class="badge ${badgeClass(task.status)}">${task.status}</span>
      </div>
    </div>
    <div class="task-actions">
      <select class="status-select" data-id="${task.id}">
        ${statusOptions(task.status)}
      </select>
      <button class="btn btn-delete" data-action="delete" data-id="${task.id}">Delete</button>
    </div>
  `;

  return row;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function loadTasks() {
  try {
    const res = await fetch(API.tasks);
    if (!res.ok) throw new Error("Failed to load tasks");
    const tasks = await res.json();

    el.taskList.innerHTML = "";

    if (!tasks || tasks.length === 0) {
      el.taskList.appendChild(el.emptyState);
      el.emptyState.style.display = "block";
    } else {
      tasks.forEach((task) => el.taskList.appendChild(taskRow(task)));
    }

    renderCounts(tasks || []);
  } catch (err) {
    el.taskList.innerHTML = `<p class="empty-state">Could not load tasks. Check the backend connection.</p>`;
  }
}

async function addTask(event) {
  event.preventDefault();
  el.formError.textContent = "";

  const title = el.titleInput.value.trim();
  const description = el.descriptionInput.value.trim();

  if (!title) {
    el.formError.textContent = "Title is required.";
    return;
  }

  try {
    const res = await fetch(API.tasks, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      el.formError.textContent = data.error || "Could not add task.";
      return;
    }

    el.titleInput.value = "";
    el.descriptionInput.value = "";
    await refreshAll();
  } catch (err) {
    el.formError.textContent = "Network error - could not reach backend.";
  }
}

async function changeStatus(taskId, newStatus) {
  try {
    // PUT requires a full payload, so fetch the task's current title/
    // description first and resend them alongside the new status.
    const current = await fetch(`${API.tasks}/${taskId}`).then((r) => r.json());

    const res = await fetch(`${API.tasks}/${taskId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: current.title,
        description: current.description || "",
        status: newStatus,
      }),
    });
    if (res.ok) await refreshAll();
  } catch (err) {
    // Silently ignore - next refresh will reflect true state.
  }
}

async function deleteTask(taskId) {
  try {
    const res = await fetch(`${API.tasks}/${taskId}`, { method: "DELETE" });
    if (res.ok) await refreshAll();
  } catch (err) {
    // Silently ignore - next refresh will reflect true state.
  }
}

el.taskList.addEventListener("click", (event) => {
  const btn = event.target.closest("button[data-action]");
  if (!btn) return;
  if (btn.dataset.action === "delete") deleteTask(btn.dataset.id);
});

el.taskList.addEventListener("change", (event) => {
  const select = event.target.closest(".status-select");
  if (!select) return;
  changeStatus(select.dataset.id, select.value);
});

el.addForm.addEventListener("submit", addTask);
el.refreshBtn.addEventListener("click", refreshAll);

async function refreshAll() {
  await Promise.all([checkBackendHealth(), checkDbHealth(), loadTasks()]);
}

refreshAll();
setInterval(refreshAll, 15000); // keep health + counts fresh during a demo
