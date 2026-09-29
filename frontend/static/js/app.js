/* ==========================================================================
   Campus Placement Portal — vanilla JS app
   ========================================================================== */

(function () {
  "use strict";

  const CSRF = document.querySelector('meta[name="csrf-token"]')?.content || "";

  /* ------------------------------ Toast ------------------------------ */

  function toast(message, type) {
    type = type || "info";
    const stack = document.getElementById("toastStack");
    const el = document.createElement("div");
    el.className = "toast toast-" + type;
    el.innerHTML = "<span></span><button class='toast-close'>&times;</button>";
    el.querySelector("span").textContent = message;
    el.querySelector(".toast-close").addEventListener("click", () => dismiss(el));
    stack.appendChild(el);
    setTimeout(() => dismiss(el), 4500);
    return el;
  }

  function dismiss(el) {
    el.classList.add("leaving");
    setTimeout(() => el.remove(), 220);
  }

  document.querySelectorAll("[data-auto-dismiss]").forEach((el) => {
    setTimeout(() => dismiss(el), 5000);
    el.querySelector(".toast-close")?.addEventListener("click", () => dismiss(el));
  });

  /* ------------------------------ API fetch ------------------------------ */

  async function api(path, options) {
    options = options || {};
    options.headers = Object.assign(
      { "X-CSRF-Token": CSRF, Accept: "application/json" },
      options.headers || {}
    );
    if (options.json !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(options.json);
      delete options.json;
    }
    const res = await fetch(path, options);
    let payload = null;
    try {
      payload = await res.json();
    } catch (e) {
      /* non-JSON response */
    }
    if (res.status === 401 && !payload) {
      window.location.href = "/login";
      throw new Error("unauthenticated");
    }
    if (!res.ok) {
      const msg = payload?.error?.message || "Something went wrong. Please try again.";
      const err = new Error(msg);
      err.code = payload?.error?.code;
      err.details = payload?.error?.details;
      err.status = res.status;
      throw err;
    }
    return payload;
  }

  /* ------------------------------ Modal ------------------------------ */

  const backdrop = document.getElementById("modalBackdrop");
  const modalTitle = document.getElementById("modalTitle");
  const modalBody = document.getElementById("modalBody");
  const modalFooter = document.getElementById("modalFooter");

  function openModal({ title, body, footer, size }) {
    modalTitle.textContent = title || "";
    modalBody.innerHTML = body || "";
    modalFooter.innerHTML = footer || "";
    backdrop.hidden = false;
    backdrop.classList.toggle("modal-lg", size === "lg");
    document.body.style.overflow = "hidden";
  }
  function closeModal() {
    backdrop.hidden = true;
    document.body.style.overflow = "";
  }
  document.getElementById("modalClose")?.addEventListener("click", closeModal);
  backdrop?.addEventListener("click", (e) => {
    if (e.target === backdrop) closeModal();
  });

  function confirmDialog({ title, message, confirmText, danger, onConfirm }) {
    const footer = `
      <button class="btn btn-ghost" data-cancel>Cancel</button>
      <button class="btn ${danger ? "btn-danger" : "btn-primary"}" data-confirm>${confirmText || "Confirm"}</button>`;
    openModal({ title: title || "Are you sure?", body: `<p>${message}</p>`, footer });
    modalFooter.querySelector("[data-cancel]").addEventListener("click", closeModal);
    modalFooter.querySelector("[data-confirm]").addEventListener("click", async () => {
      closeModal();
      await onConfirm();
    });
  }

  /* ------------------------------ Navbar (mobile menu) ------------------------------ */

  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");
  navToggle?.addEventListener("click", () => {
    const open = navLinks.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(open));
  });
  // close the mobile menu when a link is chosen
  navLinks?.addEventListener("click", (e) => {
    if (e.target.closest("a") && navLinks.classList.contains("open")) {
      navLinks.classList.remove("open");
      navToggle.setAttribute("aria-expanded", "false");
    }
  });

  /* dropdowns */
  function bindDropdown(toggleId, dropdownId) {
    const toggle = document.getElementById(toggleId);
    const dd = document.getElementById(dropdownId);
    if (!toggle || !dd) return;
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = dd.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", (e) => {
      if (!dd.contains(e.target) && e.target !== toggle && !toggle.contains(e.target)) {
        dd.classList.remove("open");
      }
    });
  }
  bindDropdown("notifToggle", "notifDropdown");
  bindDropdown("userMenuToggle", "userDropdown");

  /* ------------------------------ Scroll progress bar ------------------------------ */

  const progressBar = document.getElementById("scrollProgress");
  function updateScrollProgress() {
    if (!progressBar) return;
    const doc = document.documentElement;
    const max = doc.scrollHeight - window.innerHeight;
    progressBar.style.transform = `scaleX(${max > 0 ? Math.min(window.scrollY / max, 1) : 0})`;
  }

  /* ------------------------------ Back to top ------------------------------ */

  const backToTop = document.getElementById("backToTop");
  function updateBackToTop() {
    if (!backToTop) return;
    backToTop.classList.toggle("visible", window.scrollY > 400);
  }

  window.addEventListener("scroll", () => {
    updateScrollProgress();
    updateBackToTop();
  }, { passive: true });
  updateScrollProgress();
  updateBackToTop();

  backToTop?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  /* ------------------------------ Cookie banner ------------------------------ */

  const COOKIE_KEY = "campusplace-cookie-ok";
  const cookieBanner = document.getElementById("cookieBanner");
  if (cookieBanner && !localStorage.getItem(COOKIE_KEY)) {
    // slide in after a beat so the page settles first
    setTimeout(() => {
      cookieBanner.classList.remove("hidden");
      document.body.classList.add("has-cookie-banner");
    }, 600);
  }
  document.getElementById("cookieAccept")?.addEventListener("click", () => {
    localStorage.setItem(COOKIE_KEY, "1");
    cookieBanner.classList.add("hidden");
    document.body.classList.remove("has-cookie-banner");
  });

  /* ------------------------------ Copy buttons ------------------------------ */

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      ta.remove();
    }
  }

  document.querySelectorAll("[data-copy], [data-copy-text]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      let text = "";
      if (btn.dataset.copyText) {
        text = btn.dataset.copyText.trim();
      } else {
        const source = btn.dataset.copy
          ? document.querySelector(btn.dataset.copy)
          : btn.previousElementSibling;
        text = (source?.textContent || "").trim();
      }
      if (!text) return;
      try {
        await copyText(text);
        const original = btn.textContent;
        btn.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.textContent = original;
          btn.classList.remove("copied");
        }, 1600);
      } catch (err) {
        toast("Could not copy to clipboard.", "error");
      }
    });
  });

  /* ------------------------------ Password visibility toggle ------------------------------ */

  const EYE = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12z"/><circle cx="12" cy="12" r="2.8"/></svg>';
  const EYE_OFF = '<svg class="eye-off" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17.94 17.94A10.5 10.5 0 0 1 12 19.5C5.5 19.5 2 12 2 12a19 19 0 0 1 4.06-5.06M9.9 5.1A10.9 10.9 0 0 1 12 4.5c6.5 0 10 7.5 10 7.5a19 19 0 0 1-2.16 3.19"/><path d="m2 2 20 20"/><path d="M9.88 9.88a2.8 2.8 0 1 0 3.95 4.24"/></svg>';

  document.querySelectorAll("[data-pw-toggle]").forEach((input) => {
    const wrap = document.createElement("div");
    wrap.className = "pw-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pw-toggle";
    btn.setAttribute("aria-label", "Show password");
    btn.innerHTML = EYE + EYE_OFF;
    wrap.appendChild(btn);
    btn.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      btn.classList.toggle("visible", show);
      btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  /* ------------------------------ Notifications ------------------------------ */

  async function loadNotifications() {
    const list = document.getElementById("notifList");
    if (!list) return;
    list.innerHTML =
      '<div class="skeleton-row" style="padding:16px;"><div class="skeleton w-60"></div><div class="skeleton"></div><div class="skeleton w-40"></div></div>' +
      '<div class="skeleton-row" style="padding:16px;"><div class="skeleton w-60"></div><div class="skeleton"></div><div class="skeleton w-40"></div></div>';
    try {
      const res = await api("/api/v1/notifications?limit=6");
      const items = res.data.notifications || [];
      if (!items.length) {
        list.innerHTML = '<div class="dropdown-empty">You are all caught up.</div>';
        return;
      }
      list.innerHTML = items
        .map(
          (n) => `
        <div class="notif-item ${n.is_read ? "read" : "unread"}" data-notif-id="${n.id}">
          <span class="ni-dot"></span>
          <div>
            <div class="ni-title">${esc(n.title)}</div>
            <div class="ni-msg">${esc(n.message)}</div>
            <div class="ni-time">${timeAgo(n.created_at)}</div>
          </div>
        </div>`
        )
        .join("");
      list.querySelectorAll("[data-notif-id]").forEach((el) => {
        el.addEventListener("click", async () => {
          if (!el.classList.contains("unread")) return;
          try {
            await api(`/api/v1/notifications/${el.dataset.notifId}/read`, { method: "POST" });
            el.classList.remove("unread");
            el.classList.add("read");
            refreshNotifDot();
          } catch (err) {
            toast(err.message, "error");
          }
        });
      });
    } catch (err) {
      list.innerHTML = '<div class="dropdown-empty">Could not load notifications.</div>';
    }
  }
  loadNotifications();

  const markAllBtn = document.getElementById("markAllRead");
  markAllBtn?.addEventListener("click", async () => {
    try {
      await api("/api/v1/notifications/read-all", { method: "POST" });
      document.querySelectorAll(".notif-item.unread").forEach((el) => {
        el.classList.remove("unread");
        el.classList.add("read");
      });
      refreshNotifDot();
      toast("All notifications marked as read.", "success");
    } catch (err) {
      toast(err.message, "error");
    }
  });

  function refreshNotifDot() {
    const dot = document.querySelector(".notif-dot");
    if (dot) dot.remove();
  }

  function esc(s) {
    const div = document.createElement("div");
    div.textContent = s || "";
    return div.innerHTML;
  }

  function timeAgo(iso) {
    if (!iso) return "";
    const then = new Date(iso);
    const diff = (Date.now() - then.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return then.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  }

  /* ------------------------------ Logout ------------------------------ */

  document.getElementById("logoutBtn")?.addEventListener("click", async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } catch (e) {
      /* ignore */
    }
    window.location.href = "/";
  });

  /* ------------------------------ Auth + data forms: loading, success, error ------------------------------ */

  function setBtnLoading(btn, loading, label) {
    if (!btn) return;
    if (loading) {
      btn.dataset.original = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="btn-spinner" aria-hidden="true"></span>' + (label || "Please wait…");
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.original || label || btn.textContent;
    }
  }

  document.querySelectorAll("form[data-api]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearFieldErrors(form);
      form.classList.remove("form-success");
      form.querySelectorAll(".form-success-message, .form-error-message").forEach((el) => el.remove());
      const btn = form.querySelector("[type=submit]");
      setBtnLoading(btn, true);
      const payload = {};
      form.querySelectorAll("[name]").forEach((el) => {
        if (el.type === "checkbox") payload[el.name] = el.checked;
        else payload[el.name] = el.value;
      });
      try {
        const res = await api(form.dataset.api, {
          method: form.dataset.method || "POST",
          json: payload,
        });
        // success state: banner inside the form + green inputs
        const okMsg = document.createElement("div");
        okMsg.className = "form-success-message";
        okMsg.setAttribute("role", "status");
        okMsg.textContent = res.message || "Saved.";
        form.prepend(okMsg);
        form.classList.add("form-success");
        form
          .querySelectorAll(".input")
          .forEach((el) => el.classList.add("input-success"));
        toast(res.message || "Done!", "success");
        const redirect = form.dataset.redirect || res?.data?.redirect;
        if (redirect) {
          setTimeout(() => (window.location.href = redirect), 700);
        } else if (form.dataset.reload === "1") {
          setTimeout(() => window.location.reload(), 800);
        } else {
          setBtnLoading(btn, false);
        }
      } catch (err) {
        // error state: banner inside the form + red inputs + field errors
        const errMsg = document.createElement("div");
        errMsg.className = "form-error-message";
        errMsg.setAttribute("role", "alert");
        errMsg.textContent = err.message || "Something went wrong.";
        form.prepend(errMsg);
        if (err.code === "VALIDATION_ERROR" && err.status === 422 && err.details) {
          showFieldErrors(form, err.details);
        }
        toast(err.message, "error");
        setBtnLoading(btn, false);
      }
    });
  });

  function showFieldErrors(form, details) {
    for (const [name, messages] of Object.entries(details)) {
      const input = form.querySelector(`[name="${name}"]`);
      if (!input) continue;
      input.classList.add("input-error");
      let err = input.closest(".form-group")?.querySelector(".field-error");
      if (!err) {
        err = document.createElement("div");
        err.className = "field-error";
        input.closest(".form-group")?.appendChild(err);
      }
      err.textContent = Array.isArray(messages) ? messages.join(", ") : String(messages);
    }
  }
  function clearFieldErrors(form) {
    form.querySelectorAll(".field-error").forEach((el) => el.remove());
    form.querySelectorAll(".input-error").forEach((el) => el.classList.remove("input-error"));
    form.querySelectorAll(".input-success").forEach((el) => el.classList.remove("input-success"));
  }

  /* password strength */
  document.querySelectorAll("input[data-pw-meter]").forEach((input) => {
    const meter = document.querySelector(input.dataset.pwMeter);
    if (!meter) return;
    input.addEventListener("input", () => {
      const v = input.value;
      let score = 0;
      if (v.length >= 8) score++;
      if (v.length >= 12) score++;
      if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
      if (/\d/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      const pct = Math.min((score / 5) * 100, 100);
      meter.querySelector("i").style.width = pct + "%";
      meter.querySelector("i").style.background =
        pct < 40 ? "var(--danger)" : pct < 70 ? "var(--warning)" : "var(--success)";
    });
  });

  /* role picker on register pages */
  document.querySelectorAll(".role-option").forEach((opt) => {
    opt.addEventListener("click", () => {
      document.querySelectorAll(".role-option").forEach((o) => o.classList.remove("selected"));
      opt.classList.add("selected");
    });
  });

  /* ------------------------------ Resume upload ------------------------------ */

  const dropzone = document.getElementById("resumeDropzone");
  const resumeInput = document.getElementById("resumeFile");
  if (dropzone && resumeInput) {
    ["dragover", "dragenter"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      })
    );
    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer.files.length) resumeInput.files = e.dataTransfer.files;
    });
    dropzone.addEventListener("click", () => resumeInput.click());
    resumeInput.addEventListener("change", () => uploadResume(resumeInput.files[0]));
  }

  async function uploadResume(file) {
    if (!file) return;
    const dz = document.getElementById("resumeDropzone");
    const status = document.getElementById("resumeUploadStatus");
    if (status) status.textContent = "Uploading…";
    if (dz) dz.querySelector(".dz-text").textContent = "Uploading…";
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api("/api/v1/student/resumes", { method: "POST", body: fd });
      toast(res.message || "Resume uploaded!", "success");
      setTimeout(() => window.location.reload(), 700);
    } catch (err) {
      toast(err.message, "error");
      if (status) status.textContent = "";
      if (dz) dz.querySelector(".dz-text").textContent = "Click or drop your resume here";
    }
  }

  document.querySelectorAll("[data-delete-resume]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      confirmDialog({
        title: "Delete resume",
        message: "This resume will be permanently removed.",
        confirmText: "Delete",
        danger: true,
        onConfirm: async () => {
          try {
            await api(`/api/v1/student/resumes/${btn.dataset.deleteResume}`, { method: "DELETE" });
            toast("Resume deleted.", "success");
            setTimeout(() => window.location.reload(), 500);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Resume preview ------------------------------ */

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-preview-resume]");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const resumeId = btn.dataset.previewResume;
    window.open(`/resumes/${resumeId}/preview`, "_blank");
  });

  /* ------------------------------ Apply flow ------------------------------ */

  document.querySelectorAll("[data-apply]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const oppId = btn.dataset.apply;
      try {
        const res = await api("/api/v1/student/resumes");
        const resumes = (res.data.resumes || []).filter((r) => r.is_active);
        let body;
        if (resumes.length === 0) {
          body = `<p>You need an active resume before applying.</p><p class="small muted">Upload one from your profile page.</p>`;
          openModal({
            title: "Resume required",
            body,
            footer: `<a class="btn btn-primary" href="/student/profile">Go to profile</a>`,
          });
          return;
        }
        body = `
          <p class="mb-2">Choose the resume to attach to this application:</p>
          ${resumes
            .map(
              (r) => `
            <label class="check-row" style="padding:10px;border:1px solid var(--line);border-radius:10px;margin-bottom:8px;cursor:pointer;display:flex;align-items:center;gap:10px;">
              <input type="radio" name="resume" value="${r.id}" ${r.id === resumes[0].id ? "checked" : ""}>
              <span class="grow"><strong>${esc(r.file_name)}</strong> <span class="small muted">(${r.file_size} bytes)</span></span>
              <button type="button" class="link-btn small" data-preview-resume="${r.id}">Preview</button>
            </label>`
            )
            .join("")}`;
        const footer = `<button class="btn btn-ghost" data-cancel>Cancel</button>
          <button class="btn btn-primary" data-confirm>Submit application</button>`;
        openModal({ title: "Apply now", body, footer });
        modalFooter.querySelector("[data-cancel]").addEventListener("click", closeModal);
        modalFooter.querySelector("[data-confirm]").addEventListener("click", async (ev) => {
          const confirmBtn = ev.currentTarget;
          confirmBtn.disabled = true;
          const resumeId = modalBody.querySelector('input[name="resume"]:checked')?.value;
          try {
            const r = await api(`/api/v1/student/opportunities/${oppId}/apply`, {
              method: "POST",
              json: { resume_id: resumeId ? Number(resumeId) : null },
            });
            closeModal();
            toast(r.message, "success");
            setTimeout(() => (window.location.href = "/student/applications"), 700);
          } catch (err) {
            toast(err.message, "error");
            confirmBtn.disabled = false;
          }
        });
      } catch (err) {
        toast(err.message, "error");
      }
    });
  });

  /* ------------------------------ Applicant status actions ------------------------------ */

  document.querySelectorAll("[data-status-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { statusAction: appId, status, statusTarget } = btn.dataset;
      const label = btn.textContent.trim();
      confirmDialog({
        title: `Move to "${statusTarget || status}"?`,
        message: "This will change the application status and notify the student.",
        confirmText: label,
        onConfirm: async () => {
          try {
            const res = await api(`/api/v1/recruiter/applications/${appId}/status`, {
              method: "PATCH",
              json: { status },
            });
            toast(res.message, "success");
            setTimeout(() => window.location.reload(), 600);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Admin approve / reject ------------------------------ */

  document.querySelectorAll("[data-admin-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { adminAction: url, adminType, adminName } = btn.dataset;
      const isApprove = url.includes("/approve");
      confirmDialog({
        title: isApprove ? "Approve?" : "Reject?",
        message: `${isApprove ? "Approve" : "Reject"} ${adminName || "this item"}? ${
          isApprove ? "The user will be notified." : ""
        }`,
        confirmText: isApprove ? "Approve" : "Reject",
        danger: !isApprove,
        onConfirm: async () => {
          try {
            const res = await api(url, { method: "PATCH" });
            toast(res.message, "success");
            setTimeout(() => window.location.reload(), 600);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Suspend / reactivate ------------------------------ */

  document.querySelectorAll("[data-user-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const url = btn.dataset.userAction;
      const suspend = url.includes("/suspend");
      confirmDialog({
        title: suspend ? "Suspend user?" : "Reactivate user?",
        message: suspend
          ? "The user will lose access until reactivated."
          : "The user will regain access to the portal.",
        confirmText: suspend ? "Suspend" : "Reactivate",
        danger: suspend,
        onConfirm: async () => {
          try {
            const res = await api(url, { method: "PATCH" });
            toast(res.message, "success");
            setTimeout(() => window.location.reload(), 600);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Interview scheduling ------------------------------ */

  document.querySelectorAll("[data-schedule-interview]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const appId = btn.dataset.scheduleInterview;
      const body = `
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label" for="iv-date">Date</label>
            <input class="input" type="date" id="iv-date" required>
          </div>
          <div class="form-group">
            <label class="form-label" for="iv-time">Time</label>
            <input class="input" type="time" id="iv-time" required>
          </div>
          <div class="form-group">
            <label class="form-label" for="iv-mode">Mode</label>
            <select class="input" id="iv-mode">
              <option value="ONLINE">Online</option>
              <option value="OFFICE">At office</option>
              <option value="PHONE">Phone</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="iv-location">Location</label>
            <input class="input" type="text" id="iv-location" placeholder="Office address / city">
          </div>
          <div class="form-group full">
            <label class="form-label" for="iv-meeting">Meeting details</label>
            <input class="input" type="text" id="iv-meeting" placeholder="Link or room number">
          </div>
          <div class="form-group full">
            <label class="form-label" for="iv-instructions">Additional instructions</label>
            <textarea class="input" id="iv-instructions" rows="3"></textarea>
          </div>
        </div>`;
      const footer = `<button class="btn btn-ghost" data-cancel>Cancel</button>
        <button class="btn btn-primary" data-confirm>Schedule interview</button>`;
      openModal({ title: "Schedule interview", body, footer });
      modalFooter.querySelector("[data-cancel]").addEventListener("click", closeModal);
      modalFooter.querySelector("[data-confirm]").addEventListener("click", async (ev) => {
        const confirmBtn = ev.currentTarget;
        confirmBtn.disabled = true;
        const payload = {
          scheduled_date: modalBody.querySelector("#iv-date").value,
          scheduled_time: modalBody.querySelector("#iv-time").value,
          mode: modalBody.querySelector("#iv-mode").value,
          location: modalBody.querySelector("#iv-location").value,
          meeting_details: modalBody.querySelector("#iv-meeting").value,
          additional_instructions: modalBody.querySelector("#iv-instructions").value,
        };
        if (!payload.scheduled_date || !payload.scheduled_time) {
          toast("Please pick a date and time.", "error");
          confirmBtn.disabled = false;
          return;
        }
        try {
          const res = await api(`/api/v1/recruiter/applications/${appId}/interviews`, {
            method: "POST",
            json: payload,
          });
          closeModal();
          const conflicts = res.data.conflicts || [];
          if (conflicts.length) {
            toast(`Scheduled. Note: the student has ${conflicts.length} overlapping interview(s).`, "warning");
          } else {
            toast(res.message, "success");
          }
          setTimeout(() => window.location.reload(), 800);
        } catch (err) {
          toast(err.message, "error");
          confirmBtn.disabled = false;
        }
      });
    });
  });

  /* cancel / complete interview */
  document.querySelectorAll("[data-interview-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { interviewAction: url, interviewType, interviewLabel } = btn.dataset;
      const isCancel = url.includes("/cancel");
      confirmDialog({
        title: isCancel ? "Cancel interview?" : "Mark completed?",
        message: isCancel
          ? `The interview for ${interviewLabel || "this candidate"} will be cancelled and the student notified.`
          : "Mark this interview as completed?",
        confirmText: isCancel ? "Cancel interview" : "Mark completed",
        danger: isCancel,
        onConfirm: async () => {
          try {
            const res = await api(url, { method: "POST" });
            toast(res.message, "success");
            setTimeout(() => window.location.reload(), 600);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Opportunity actions (recruiter) ------------------------------ */

  document.querySelectorAll("[data-opportunity-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { opportunityAction: url, opportunityActionName } = btn.dataset;
      const action = url.includes("/submit")
        ? "submit"
        : url.includes("/close")
        ? "close"
        : url.includes("/reopen")
        ? "reopen"
        : "archive";
      const actionMessages = {
        submit: "sent for admin review",
        close: "closed to new applications",
        reopen: "reopened for applications",
        archive: "archived",
      };
      confirmDialog({
        title: `${action[0].toUpperCase() + action.slice(1)} opportunity?`,
        message: `"${opportunityActionName}" will be ${actionMessages[action]}.`,
        confirmText: action[0].toUpperCase() + action.slice(1),
        danger: action === "close" || action === "archive",
        onConfirm: async () => {
          try {
            const res = await api(url, { method: "POST" });
            toast(res.message, "success");
            setTimeout(() => window.location.reload(), 700);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Delete opportunity (recruiter) ------------------------------ */

  document.querySelectorAll("[data-delete-opportunity]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const { deleteOpportunity: url, deleteOpportunityName } = btn.dataset;
      confirmDialog({
        title: "Delete opportunity?",
        message: `"${deleteOpportunityName}" will be permanently deleted. This action cannot be undone.`,
        confirmText: "Delete",
        danger: true,
        onConfirm: async () => {
          try {
            const res = await api(url, { method: "DELETE" });
            toast(res.message, "success");
            setTimeout(() => (window.location.href = "/recruiter/opportunities"), 700);
          } catch (err) {
            toast(err.message, "error");
          }
        },
      });
    });
  });

  /* ------------------------------ Mark notification read (page) ------------------------------ */

  document.querySelectorAll("[data-notif-page]").forEach((el) => {
    el.addEventListener("click", async () => {
      const id = el.dataset.notifPage;
      if (el.classList.contains("unread")) {
        try {
          await api(`/api/v1/notifications/${id}/read`, { method: "POST" });
          el.classList.remove("unread");
          el.classList.add("read");
          refreshNotifDot();
        } catch (err) {
          /* non-critical */
        }
      }
    });
  });

  /* ------------------------------ Filters auto-submit ------------------------------ */

  const filterForm = document.getElementById("filterForm");
  filterForm?.querySelectorAll("select, input").forEach((el) => {
    const evt = el.tagName === "SELECT" ? "change" : "input";
    let timer = null;
    el.addEventListener(evt, () => {
      if (el.tagName === "SELECT") {
        filterForm.submit();
        return;
      }
      clearTimeout(timer);
      timer = setTimeout(() => filterForm.submit(), 550);
    });
  });

  /* ------------------------------ Theme Toggle ------------------------------ */

  const THEME_KEY = "campusplace-theme";
  const root = document.documentElement;

  function getPreferredTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === "dark" || stored === "light") return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }

  /* Apply stored / system theme immediately (before paint) */
  applyTheme(getPreferredTheme());

  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = root.getAttribute("data-theme");
      applyTheme(current === "dark" ? "light" : "dark");
    });
  }

  /* Listen for OS theme changes */
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem(THEME_KEY)) {
      applyTheme(e.matches ? "dark" : "light");
    }
  });

  /* Expose helpers used by inline scripts in templates */
  window.api = api;
  window.toast = toast;
})();
