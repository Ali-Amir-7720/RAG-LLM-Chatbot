from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, NamedTuple

import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


class TocEntry(NamedTuple):
    title: str
    level: int  # 1=h1,2=h2
    page: int


@dataclass(frozen=True)
class Theme:
    primary: tuple[int, int, int]
    text: tuple[int, int, int]
    muted: tuple[int, int, int]
    line: tuple[int, int, int]
    card: tuple[int, int, int]


THEME = Theme(
    primary=(36, 99, 235),  # blue
    text=(25, 25, 25),
    muted=(90, 90, 90),
    line=(225, 225, 225),
    card=(248, 250, 252),
)


@dataclass(frozen=True)
class Style:
    font: str
    size: int
    leading: float


STYLES = {
    "cover_title": Style("UI", 26, 1.2),
    "cover_sub": Style("UI", 12, 1.4),
    "h1": Style("UI", 16, 1.35),
    "h2": Style("UI", 12, 1.45),
    "body": Style("UI", 10, 1.6),
    "small": Style("UI", 9, 1.5),
    "mono": Style("Mono", 9, 1.45),
}


class Pdf(FPDF):
    def __init__(self, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.doc_title = title

    def header(self) -> None:
        if self.page_no() <= 2:
            return  # cover + toc
        self.set_draw_color(*THEME.line)
        self.set_line_width(0.2)
        self.line(self.l_margin, 12, self.w - self.r_margin, 12)
        self.set_y(7.5)
        self.set_font("UI", "", 8)
        self.set_text_color(*THEME.muted)
        self.cell(0, 6, self.doc_title, align="L")

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("UI", "", 8)
        self.set_text_color(*THEME.muted)
        self.cell(0, 8, f"{self.page_no()}", align="C")


def register_fonts(pdf: Pdf) -> None:
    fonts_dir = Path(r"C:\Windows\Fonts")
    ui_regular = fonts_dir / "segoeui.ttf"
    ui_bold = fonts_dir / "segoeuib.ttf"
    ui_italic = fonts_dir / "segoeuii.ttf"
    mono_regular = fonts_dir / "consola.ttf"

    for p in (ui_regular, ui_bold, mono_regular):
        if not p.exists():
            raise SystemExit(f"Missing font: {p}")
    # italic is optional; fallback to regular if missing
    if not ui_italic.exists():
        ui_italic = ui_regular

    pdf.add_font("UI", style="", fname=str(ui_regular))
    pdf.add_font("UI", style="B", fname=str(ui_bold))
    pdf.add_font("UI", style="I", fname=str(ui_italic))
    pdf.add_font("Mono", style="", fname=str(mono_regular))


def mm_to_in(mm: float) -> float:
    return mm / 25.4


def save_flow_diagram(path: Path, title: str, steps: list[str]) -> None:
    """
    Generate a simple left-to-right workflow diagram as a PNG.
    """
    # Layout
    n = len(steps)
    w_mm = 180
    h_mm = 55 if n <= 6 else 70
    dpi = 200
    fig_w = mm_to_in(w_mm)
    fig_h = mm_to_in(h_mm)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    ax.set_axis_off()

    # Coordinate system 0..1
    xs = np.linspace(0.06, 0.94, n)
    y = 0.55

    box_w = min(0.20, 0.82 / n + 0.06)
    box_h = 0.22

    ax.text(
        0.02,
        0.95,
        title,
        fontsize=11,
        fontweight="bold",
        color=np.array(THEME.text) / 255.0,
        ha="left",
        va="top",
        transform=ax.transAxes,
    )

    for i, (x, step) in enumerate(zip(xs, steps, strict=False)):
        x0 = x - box_w / 2
        y0 = y - box_h / 2
        rect = plt.Rectangle(
            (x0, y0),
            box_w,
            box_h,
            linewidth=1,
            edgecolor=np.array(THEME.primary) / 255.0,
            facecolor=np.array(THEME.card) / 255.0,
            transform=ax.transAxes,
        )
        ax.add_patch(rect)
        ax.text(
            x,
            y,
            step,
            fontsize=9,
            color=np.array(THEME.text) / 255.0,
            ha="center",
            va="center",
            wrap=True,
            transform=ax.transAxes,
        )
        if i < n - 1:
            ax.annotate(
                "",
                xy=(xs[i + 1] - box_w / 2, y),
                xytext=(x + box_w / 2, y),
                arrowprops=dict(arrowstyle="->", lw=1.2, color=np.array(THEME.muted) / 255.0),
                xycoords=ax.transAxes,
                textcoords=ax.transAxes,
            )

    fig.tight_layout(pad=0.4)
    fig.savefig(path, transparent=False, facecolor="white")
    plt.close(fig)


def set_text(pdf: Pdf, rgb: tuple[int, int, int]) -> None:
    pdf.set_text_color(*rgb)


def h1(pdf: Pdf, text: str) -> None:
    pdf.ln(2)
    pdf.set_font(STYLES["h1"].font, "B", STYLES["h1"].size)
    set_text(pdf, THEME.text)
    pdf.multi_cell(0, STYLES["h1"].size * 0.45 * STYLES["h1"].leading, text)
    pdf.ln(1)


def h2(pdf: Pdf, text: str) -> None:
    pdf.ln(1.5)
    pdf.set_font(STYLES["h2"].font, "B", STYLES["h2"].size)
    set_text(pdf, THEME.text)
    pdf.multi_cell(0, STYLES["h2"].size * 0.45 * STYLES["h2"].leading, text)
    pdf.ln(0.5)


def p(pdf: Pdf, text: str) -> None:
    pdf.set_font(STYLES["body"].font, "", STYLES["body"].size)
    set_text(pdf, THEME.text)
    pdf.multi_cell(0, STYLES["body"].size * 0.45 * STYLES["body"].leading, text)
    pdf.ln(0.6)


def bullet_list(pdf: Pdf, items: Iterable[str]) -> None:
    pdf.set_font(STYLES["body"].font, "", STYLES["body"].size)
    set_text(pdf, THEME.text)
    lh = STYLES["body"].size * 0.45 * STYLES["body"].leading
    for item in items:
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.cell(4, lh, "•")
        pdf.set_xy(x + 4, y)
        pdf.multi_cell(0, lh, item)
        pdf.ln(0.2)


def callout(pdf: Pdf, title: str, body: str) -> None:
    x = pdf.l_margin
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # Render as a bordered card. Keep sizing simple and robust by drawing the
    # border AFTER writing content (based on y delta).
    y0 = pdf.get_y()

    pdf.set_x(x)
    pdf.set_font("UI", "B", 10)
    set_text(pdf, THEME.primary)
    pdf.multi_cell(w, 5, title)

    pdf.set_x(x)
    pdf.set_font("UI", "", 10)
    set_text(pdf, THEME.text)
    pdf.multi_cell(w, 5, body)

    y1 = pdf.get_y()
    pad = 2.0
    pdf.set_draw_color(*THEME.line)
    pdf.set_fill_color(*THEME.card)
    pdf.rect(x, y0 - pad, w, (y1 - y0) + pad * 2, style="DF")
    pdf.set_y(y1 + 1.5)


def table(pdf: Pdf, headers: list[str], rows: list[list[str]], col_widths: list[float]) -> None:
    assert len(headers) == len(col_widths)
    lh = 5.2

    pdf.set_draw_color(*THEME.line)
    pdf.set_fill_color(240, 245, 255)
    pdf.set_font("UI", "B", 9)
    set_text(pdf, THEME.text)
    for h, cw in zip(headers, col_widths, strict=True):
        pdf.cell(cw, lh, h, border=1, fill=True)
    pdf.ln(lh)

    pdf.set_font("UI", "", 9)
    pdf.set_fill_color(255, 255, 255)
    for r in rows:
        max_lines = 1
        for cell, cw in zip(r, col_widths, strict=True):
            max_lines = max(max_lines, max(1, math.ceil(len(cell) / max(12, cw * 1.6))))
        row_h = lh * max_lines
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        for i, (cell, cw) in enumerate(zip(r, col_widths, strict=True)):
            pdf.set_xy(x0 + sum(col_widths[:i]), y0)
            pdf.multi_cell(cw, lh, cell, border=1)
        pdf.set_xy(x0, y0 + row_h)

    pdf.ln(1)


def subsection(pdf: Pdf, label: str) -> None:
    """
    A consistent, compact subheading used inside each feature.
    """
    pdf.ln(0.6)
    pdf.set_font("UI", "B", 10)
    set_text(pdf, THEME.primary)
    pdf.multi_cell(0, 5.2, label)
    pdf.ln(0.2)


def feature_block(
    blocks: list[tuple[str, int, dict]],
    *,
    number: int,
    title: str,
    objective: str,
    flow_steps: list[str],
    backend_processing: list[str],
    db_ops: list[str],
    endpoints: list[str],
    error_handling: list[str],
    best_practices: list[str],
    tables_involved: list[str],
    diagram_path: str | None = None,
) -> None:
    blocks.append(("h2", 2, {"text": f"{number}. {title}"}))
    blocks.append(("p", 0, {"text": objective}))
    if diagram_path:
        blocks.append(("diagram", 0, {"path": diagram_path, "w": 180}))

    blocks.append(("sub", 0, {"label": "Workflow"}))
    blocks.append(("bullets", 0, {"items": flow_steps}))

    blocks.append(("sub", 0, {"label": "Backend processing"}))
    blocks.append(("bullets", 0, {"items": backend_processing}))

    blocks.append(("sub", 0, {"label": "Database operations"}))
    blocks.append(("bullets", 0, {"items": db_ops + [f"Tables involved: {', '.join(tables_involved)}"]}))

    blocks.append(("sub", 0, {"label": "API endpoints"}))
    blocks.append(("bullets", 0, {"items": endpoints}))

    blocks.append(("sub", 0, {"label": "Error handling"}))
    blocks.append(("bullets", 0, {"items": error_handling}))

    blocks.append(("sub", 0, {"label": "Best practices"}))
    blocks.append(("bullets", 0, {"items": best_practices}))


def build_content(tmp_dir: Path) -> list[tuple[str, int, dict]]:
    """
    Returns a list of blocks: (type, level, payload)
    type: 'h1','h2','p','bullets','diagram','table','callout'
    """
    blocks: list[tuple[str, int, dict]] = []

    blocks.append(("h1", 1, {"text": "System Overview"}))
    blocks.append(
        (
            "p",
            0,
            {
                "text": (
                    "This document provides a feature-by-feature specification for the RAG‑LLM chatbot backend. "
                    "It maps each feature to its backend workflow, database operations (PostgreSQL + pgvector), "
                    "and recommended API endpoints for a FastAPI implementation."
                )
            },
        )
    )

    blocks.append(("h2", 2, {"text": "Core loop"}))
    blocks.append(
        (
            "bullets",
            0,
            {
                "items": [
                    "Authenticate user → issue access/refresh tokens",
                    "Create or resume a conversation",
                    "Attach documents (optional) → ingestion pipeline → chunks + embeddings",
                    "Send message → build context + retrieve evidence → stream LLM answer",
                    "Store citations + feedback + usage metadata for observability",
                ]
            },
        )
    )

    # JWT rationale callout (explicitly requested)
    blocks.append(
        (
            "callout",
            0,
            {
                "title": "Why JWT access + refresh (hybrid) instead of server sessions only",
                "body": (
                    "Access tokens as short-lived JWTs allow most authenticated requests to be validated via fast "
                    "signature checks without a database lookup, which matters for chat workloads (many small calls per "
                    "conversation). Refresh tokens remain server-tracked in the user_sessions table to preserve "
                    "revocation (logout), session listing, and “log out everywhere”."
                ),
            },
        )
    )

    # ============================================================
    # Authentication & Account (1–5)
    # ============================================================
    blocks.append(("h1", 1, {"text": "Authentication & Account (Features 1–5)"}))
    auth_diagram = tmp_dir / "auth_lifecycle.png"
    save_flow_diagram(
        auth_diagram,
        "JWT hybrid lifecycle",
        ["Sign up / Login", "Access token (JWT)", "Refresh token", "Rotate/refresh", "Revoke/logout"],
    )
    blocks.append(("diagram", 0, {"path": str(auth_diagram), "w": 180}))

    feature_block(
        blocks,
        number=1,
        title="Sign up",
        objective="Register a new user account and establish the first authenticated session securely.",
        flow_steps=[
            "Client submits username, email, and password.",
            "Server validates input (length, email normalization, password policy).",
            "Server hashes password (PBKDF2; never store plaintext).",
            "Server inserts the user and creates an initial refresh session.",
            "Server returns access JWT + refresh token pair.",
        ],
        backend_processing=[
            "Normalize username/email (trim + lowercase email).",
            "Hash password with a strong KDF and per-user salt.",
            "Issue access JWT with short expiry (minutes).",
            "Generate refresh token (opaque random) and store server-side.",
        ],
        db_ops=[
            "INSERT into users with password_hash.",
            "INSERT into user_sessions with refresh_token, expires_at, device/ip (if available).",
        ],
        endpoints=[
            "POST /auth/signup",
        ],
        error_handling=[
            "409 if username/email already exists (unique indexes).",
            "400 for invalid email/password policy failures.",
        ],
        best_practices=[
            "Store refresh token in HttpOnly cookie (web) or secure keystore (mobile).",
            "Consider email verification before enabling password reset.",
        ],
        tables_involved=["users", "user_sessions"],
        diagram_path=str(auth_diagram),
    )

    feature_block(
        blocks,
        number=2,
        title="Login",
        objective="Authenticate an existing user and create a new session without reusing prior refresh tokens.",
        flow_steps=[
            "Client submits email (or username) and password.",
            "Server fetches user and verifies password hash.",
            "Server creates a new refresh session row for this device.",
            "Server returns access JWT + refresh token pair.",
        ],
        backend_processing=[
            "Constant-time password verification to reduce timing leaks.",
            "Record device + ip_address when possible for session management and anomaly detection.",
        ],
        db_ops=[
            "SELECT user by normalized email/username.",
            "INSERT new row in user_sessions (do not overwrite existing sessions).",
        ],
        endpoints=["POST /auth/login"],
        error_handling=[
            "401 for invalid credentials (avoid leaking which field is wrong).",
            "429 when rate limits are exceeded (brute-force protection).",
        ],
        best_practices=[
            "Rate-limit login per IP and per account identifier.",
            "Return identical error messages for invalid user vs invalid password.",
        ],
        tables_involved=["users", "user_sessions"],
    )

    feature_block(
        blocks,
        number=3,
        title="Token refresh (access + refresh pair)",
        objective="Allow long-lived login while keeping access tokens short-lived and revocable via refresh-session state.",
        flow_steps=[
            "Client sends refresh token when access JWT expires.",
            "Server looks up refresh token in user_sessions and checks not revoked/expired.",
            "Server issues a new access JWT.",
            "Server rotates refresh token (recommended) and returns the new pair.",
        ],
        backend_processing=[
            "Validate refresh token against server-tracked session state.",
            "Rotate refresh token to reduce replay risk.",
        ],
        db_ops=[
            "SELECT user_sessions by refresh_token; check is_revoked and expires_at.",
            "UPDATE user_sessions.refresh_token when rotating (or revoke old + insert new).",
        ],
        endpoints=["POST /auth/refresh"],
        error_handling=[
            "401 when refresh token is missing/invalid/revoked/expired.",
            "Detect refresh-replay (old token used after rotation) and revoke the entire session.",
        ],
        best_practices=[
            "Use short access token TTL; rely on refresh for continuity.",
            "Always store refresh tokens hashed at rest if feasible (defense in depth).",
        ],
        tables_involved=["user_sessions"],
    )

    feature_block(
        blocks,
        number=4,
        title="Logout (single session) + Log out everywhere",
        objective="End one session or all sessions immediately by revoking refresh sessions server-side.",
        flow_steps=[
            "Client calls logout with current refresh token (or session id).",
            "Server sets is_revoked=true for that session.",
            "For logout-all, server revokes all sessions for the user_id.",
            "Client deletes local tokens/cookies.",
        ],
        backend_processing=[
            "Revoke by flipping a server-side flag; access tokens expire naturally soon after.",
        ],
        db_ops=[
            "UPDATE user_sessions SET is_revoked=true WHERE refresh_token=… (single).",
            "UPDATE user_sessions SET is_revoked=true WHERE user_id=… (everywhere).",
        ],
        endpoints=["POST /auth/logout", "POST /auth/logout_all"],
        error_handling=[
            "200 even if session already revoked (idempotent logout).",
        ],
        best_practices=[
            "Make logout idempotent and safe to retry.",
            "Surface active sessions in UI later using user_sessions.device/ip metadata.",
        ],
        tables_involved=["user_sessions"],
    )

    feature_block(
        blocks,
        number=5,
        title="Password reset / account recovery",
        objective="Let a user regain access via email-based recovery while revoking all existing sessions upon success.",
        flow_steps=[
            "User requests password reset using email.",
            "Server issues one-time reset token (short TTL) and emails it.",
            "User submits token + new password.",
            "Server updates password_hash and revokes all sessions.",
        ],
        backend_processing=[
            "Generate reset token; store only a hash server-side.",
            "Enforce strong password policy on reset.",
        ],
        db_ops=[
            "INSERT into password_reset_tokens (recommended additional table).",
            "UPDATE users.password_hash.",
            "UPDATE user_sessions SET is_revoked=true WHERE user_id=…",
        ],
        endpoints=["POST /auth/password_reset/request", "POST /auth/password_reset/confirm"],
        error_handling=[
            "Always return 200 for reset request (do not leak whether email exists).",
            "400/401 for invalid or expired reset token on confirm.",
        ],
        best_practices=[
            "Single-use tokens; mark used_at on success.",
            "Notify user on password change and revoke all sessions.",
        ],
        tables_involved=["users", "user_sessions", "(password_reset_tokens)"],
    )

    # Conversations
    blocks.append(("h1", 1, {"text": "Conversations (Features 6–10)"}))
    conv_diagram = tmp_dir / "conversation_flow.png"
    save_flow_diagram(
        conv_diagram,
        "Conversation lifecycle",
        ["Create", "Auto-title", "List", "Archive", "Search / Export"],
    )
    blocks.append(("diagram", 0, {"path": str(conv_diagram), "w": 180}))

    blocks.append(("p", 0, {"text": "Conversations are per-user containers for message history, model settings, and attached documents."}))

    feature_block(
        blocks,
        number=6,
        title="Create conversation",
        objective="Start a new chat thread with model configuration and a default title.",
        flow_steps=[
            "Client requests a new conversation (optionally selects a model).",
            "Server inserts conversations row with default title and model_name.",
            "Client receives conversation_id and begins messaging.",
        ],
        backend_processing=[
            "Validate model_name against supported model registry (config).",
            "Initialize generation_config to {} unless provided.",
        ],
        db_ops=["INSERT into conversations (user_id, title, model_name, generation_config)."],
        endpoints=["POST /conversations"],
        error_handling=["400 if model_name is unsupported.", "401 if unauthenticated."],
        best_practices=["Keep create conversation fast; avoid LLM calls in this path."],
        tables_involved=["conversations"],
    )

    feature_block(
        blocks,
        number=7,
        title="Auto-generate conversation title",
        objective="Replace generic titles with a short, descriptive title after the first exchange.",
        flow_steps=[
            "After first user message + assistant reply, generate a short title.",
            "Update conversations.title unless user already set a custom title.",
        ],
        backend_processing=[
            "Use heuristic (first sentence) or a small LLM summarization prompt.",
            "Run asynchronously so it never blocks messaging.",
        ],
        db_ops=["UPDATE conversations SET title=… WHERE id=…"],
        endpoints=["POST /conversations/{id}/auto_title (optional internal)"],
        error_handling=["If title generation fails, keep default title (non-blocking)."],
        best_practices=["Make title generation idempotent and retryable."],
        tables_involved=["conversations", "messages"],
    )

    feature_block(
        blocks,
        number=8,
        title="List / archive / delete conversations",
        objective="Provide lifecycle management for a user’s conversation history.",
        flow_steps=[
            "List active conversations (paginated) ordered by updated_at.",
            "Archive/unarchive toggles is_archived.",
            "Delete removes conversation and cascades related rows (or soft-delete if added).",
        ],
        backend_processing=[
            "Enforce per-user scoping (user can only see/manage own conversations).",
        ],
        db_ops=[
            "SELECT conversations WHERE user_id=… AND is_archived=… ORDER BY updated_at DESC LIMIT/OFFSET.",
            "UPDATE conversations SET is_archived=true/false WHERE id=… AND user_id=…",
            "DELETE FROM conversations WHERE id=… AND user_id=… (cascades).",
        ],
        endpoints=["GET /conversations", "PATCH /conversations/{id}", "DELETE /conversations/{id}"],
        error_handling=["404 if conversation not found for user.", "409 if attempting to delete locked/exporting conv (if you add locks)."],
        best_practices=["Prefer soft-delete (deleted_at) if you need recovery/audit."],
        tables_involved=["conversations", "messages", "conversation_documents", "attachments"],
    )

    feature_block(
        blocks,
        number=9,
        title="Full-text search across past conversations",
        objective="Let users find prior chats by content quickly.",
        flow_steps=[
            "User submits a search query.",
            "Server runs full-text search over messages scoped to user conversations.",
            "Return ranked results linking to conversation + message.",
        ],
        backend_processing=[
            "Normalize query; use Postgres FTS (tsvector + GIN) or external engine.",
            "Always enforce user scoping to prevent leakage.",
        ],
        db_ops=[
            "SELECT messages WHERE conversation_id IN (user conversations) AND to_tsvector(content) @@ plainto_tsquery(q).",
        ],
        endpoints=["GET /conversations/search?q=..."],
        error_handling=["Return empty list on no matches; do not error."],
        best_practices=["Add indexes for search; paginate results and include highlights."],
        tables_involved=["messages", "conversations"],
    )

    feature_block(
        blocks,
        number=10,
        title="Export a conversation (Markdown/PDF)",
        objective="Allow users to download a conversation transcript for sharing and record-keeping.",
        flow_steps=[
            "User requests export for a conversation.",
            "Server resolves the chosen branch/path and loads messages in order.",
            "Server renders to Markdown or PDF and returns a download.",
        ],
        backend_processing=[
            "Support exporting 'active branch' using parent_message_id traversal.",
            "Include citations and document references when present.",
        ],
        db_ops=["SELECT messages WHERE conversation_id=… ORDER BY created_at ASC."],
        endpoints=["POST /conversations/{id}/export?format=md|pdf"],
        error_handling=["403/404 for unauthorized access.", "413 if export too large (or run async job)."],
        best_practices=["Generate exports asynchronously for very large conversations."],
        tables_involved=["conversations", "messages", "message_citations"],
    )

    # ============================================================
    # Messaging (11–14)
    # ============================================================
    blocks.append(("h1", 1, {"text": "Messaging (Features 11–14)"}))
    msg_diagram = tmp_dir / "messaging_flow.png"
    save_flow_diagram(
        msg_diagram,
        "Message → Answer (streaming)",
        ["Persist user msg", "Build context", "RAG retrieve", "LLM stream", "Persist answer + citations"],
    )
    blocks.append(("diagram", 0, {"path": str(msg_diagram), "w": 180}))
    feature_block(
        blocks,
        number=11,
        title="Send message + streamed LLM response",
        objective="Persist the user message, build context + retrieval, then stream the assistant response back to the client.",
        flow_steps=[
            "Client posts message content to a conversation (optionally with parent_message_id).",
            "Server inserts user message into messages.",
            "Server builds context (history + system prompt + RAG sources).",
            "Server calls LLM with streaming enabled (SSE/WebSocket).",
            "Server stores assistant message and writes citations used for grounding.",
        ],
        backend_processing=[
            "Token-budget context construction (avoid exceeding context window).",
            "If documents attached, run retrieval pipeline before LLM call.",
            "Stream partial deltas; finalize by persisting full assistant content.",
        ],
        db_ops=[
            "INSERT user message (role=user).",
            "INSERT assistant message (role=assistant) with model_name/token_count/generation_time.",
            "INSERT message_citations for retrieved chunks included.",
        ],
        endpoints=["POST /conversations/{id}/messages (stream=true)"],
        error_handling=[
            "400 for empty message content.",
            "404 if conversation_id not found for user.",
            "502/503 if LLM provider fails; persist an error state message if desired.",
        ],
        best_practices=[
            "Always store the user message before calling the LLM (auditability).",
            "Timeout and cancel LLM streams cleanly.",
        ],
        tables_involved=["messages", "conversations", "message_citations"],
        diagram_path=str(msg_diagram),
    )

    feature_block(
        blocks,
        number=12,
        title="Chat history retrieval / context building",
        objective="Assemble the exact prompt context for each model call while staying within token limits.",
        flow_steps=[
            "Identify the active branch head (latest message on the chosen path).",
            "Walk parent_message_id chain to reconstruct that path.",
            "Trim/summarize older content to fit a stable token budget.",
            "Append RAG sources (if enabled) and the system prompt.",
        ],
        backend_processing=[
            "Use token estimation; prefer trimming oldest messages first.",
            "Optionally maintain summaries for long conversations (future enhancement).",
        ],
        db_ops=[
            "SELECT messages for conversation; reconstruct branch via parent_message_id.",
        ],
        endpoints=["GET /conversations/{id}/messages?branch_head=..."],
        error_handling=["If branch_head invalid, fall back to latest linear path or return 400."],
        best_practices=["Make context assembly deterministic so behavior is predictable."],
        tables_involved=["messages", "conversations"],
    )

    feature_block(
        blocks,
        number=13,
        title="Message edit / regenerate (branching)",
        objective="Allow edits and regenerations without losing history by creating new message nodes.",
        flow_steps=[
            "Edit: create a new user message node as a sibling of the edited message (same parent).",
            "Regenerate: create a new assistant message node with parent=target user message.",
            "Client chooses which branch/path to display as active.",
        ],
        backend_processing=[
            "Never overwrite prior content; preserve audit trail.",
            "Branching enables 'what-if' exploration and safe regeneration.",
        ],
        db_ops=["INSERT new messages rows with parent_message_id set appropriately."],
        endpoints=["PATCH /messages/{id} (creates new node)", "POST /messages/{id}/regenerate"],
        error_handling=["404 if message not found for user.", "409 if attempting to edit assistant message (if disallowed)."],
        best_practices=["Expose branch navigation in UI later; keep API explicit about branch head."],
        tables_involved=["messages"],
    )

    feature_block(
        blocks,
        number=14,
        title="Thumbs up/down + text feedback",
        objective="Collect quality signals tied to assistant responses for evaluation and improvement.",
        flow_steps=[
            "User submits thumbs up/down and optional text comment on an assistant message.",
            "Server stores feedback and makes it available for analytics.",
        ],
        backend_processing=["Capture model_name, retrieval metadata, and latency alongside feedback where possible."],
        db_ops=["UPDATE messages SET is_helpful=..., feedback_text=... WHERE id=..."],
        endpoints=["POST /messages/{id}/feedback"],
        error_handling=["400 if trying to rate a non-assistant message.", "404 if message not found for user."],
        best_practices=["Keep feedback write path fast; queue analytics processing if needed."],
        tables_involved=["messages"],
    )

    # ============================================================
    # Files & documents (15–20)
    # ============================================================
    blocks.append(("h1", 1, {"text": "Files & Documents (Features 15–20)"}))
    doc_diagram = tmp_dir / "doc_pipeline.png"
    save_flow_diagram(
        doc_diagram,
        "Document pipeline",
        ["Upload", "Validate", "Dedup hash", "Extract+chunk", "Embed", "Ready"],
    )
    blocks.append(("diagram", 0, {"path": str(doc_diagram), "w": 180}))
    blocks.append(("p", 0, {"text": "Documents are stored canonically with deduplication and processed asynchronously into chunks and embeddings."}))

    feature_block(
        blocks,
        number=15,
        title="File upload (PDF/DOCX/images/audio/video)",
        objective="Accept user files, store them safely, and link them to messages and/or conversations for later retrieval.",
        flow_steps=[
            "Client uploads a file (message attachment or conversation-scoped document).",
            "Server stores metadata (mime_type, size, storage path) and creates attachment/document rows.",
            "Server links document to user and optionally to conversation for retrieval scoping.",
            "Server enqueues processing (extract → chunk → embed).",
        ],
        backend_processing=[
            "Prefer streaming uploads to storage; avoid loading entire file in memory.",
            "Use content hashing for dedup prior to heavy processing.",
        ],
        db_ops=[
            "INSERT documents (or reuse existing by content_hash).",
            "INSERT attachments if tied to a message.",
            "INSERT user_documents and conversation_documents links as applicable.",
        ],
        endpoints=["POST /uploads", "POST /uploads/{id}/complete", "POST /conversations/{id}/documents/{document_id}"],
        error_handling=["413 if too large.", "415 if unsupported file type.", "400 if metadata missing."],
        best_practices=["Use signed URLs for direct-to-object-storage uploads when available."],
        tables_involved=["documents", "attachments", "user_documents", "conversation_documents"],
        diagram_path=str(doc_diagram),
    )

    feature_block(
        blocks,
        number=16,
        title="Upload validation (size limits, MIME/type checking)",
        objective="Prevent malformed or disguised uploads from entering processing pipelines.",
        flow_steps=[
            "Reject files exceeding size limit before reading full body.",
            "Verify MIME by sniffing file signature (magic bytes).",
            "Enforce an allowlist per supported pipeline (PDF/DOCX/images/media).",
        ],
        backend_processing=["Log validation failures for abuse monitoring.", "Optionally run malware scanning in production."],
        db_ops=["Store validation failure reason in logs or a processing-events table (recommended)."],
        endpoints=["POST /uploads (validation)"],
        error_handling=["415 for unsupported types.", "413 for size limit exceeded."],
        best_practices=["Do not trust filenames or client-supplied Content-Type headers."],
        tables_involved=["documents", "attachments"],
    )

    feature_block(
        blocks,
        number=17,
        title="Document processing pipeline (extract → chunk → embed → ready)",
        objective="Convert uploaded files into retrievable chunks and embeddings for RAG.",
        flow_steps=[
            "Worker picks documents in processing state.",
            "Extract text (PDF/DOCX/OCR/transcription).",
            "Chunk text into stable, ordered pieces with metadata.",
            "Embed each chunk and store vectors.",
            "Mark document ready or failed.",
        ],
        backend_processing=[
            "Use deterministic chunking (size + overlap) for stable retrieval behavior.",
            "Ensure embedding dimensions match vector column (currently VECTOR(1536)).",
        ],
        db_ops=[
            "UPDATE documents.status=processing/ready/failed.",
            "INSERT document_chunks; INSERT chunk_embeddings.",
        ],
        endpoints=["(internal worker) /documents/{id}/process"],
        error_handling=["Mark documents.status=failed on extraction/embedding errors; keep error details in logs/events."],
        best_practices=["Run processing async; expose status polling endpoint for UI progress."],
        tables_involved=["documents", "document_chunks", "chunk_embeddings", "embedding_models"],
    )

    feature_block(
        blocks,
        number=18,
        title="Global document dedup (content hash)",
        objective="Avoid re-upload, re-chunk, and re-embed of identical content across users/conversations.",
        flow_steps=[
            "Compute SHA-256 content_hash for uploaded bytes.",
            "If documents.content_hash exists, reuse document and derived artifacts.",
            "Link existing document into the user library and conversation scope.",
        ],
        backend_processing=["Normalize hash computation (raw bytes) so dedup is stable."],
        db_ops=[
            "SELECT documents by content_hash; if present, INSERT links into user_documents/conversation_documents.",
        ],
        endpoints=["(part of) POST /uploads/{id}/complete"],
        error_handling=["Handle hash collisions as extremely unlikely; still treat content_hash as unique key."],
        best_practices=["Dedup saves cost and latency; keep it before heavy processing."],
        tables_involved=["documents", "user_documents", "conversation_documents"],
    )

    feature_block(
        blocks,
        number=19,
        title="Audio/video transcription pipeline",
        objective="Turn media into searchable text for retrieval and citations.",
        flow_steps=[
            "Extract audio from media (if video).",
            "Transcribe speech to text with timestamps.",
            "Chunk transcript and embed.",
            "Mark document ready.",
        ],
        backend_processing=["Store timestamps as metadata (future schema extension) for time-based citations."],
        db_ops=["INSERT document_chunks + chunk_embeddings; UPDATE documents.status."],
        endpoints=["(internal worker) /media/{id}/transcribe"],
        error_handling=["Mark failed on transcription errors; allow retries."],
        best_practices=["Separate transcription from embedding for clearer retries/observability."],
        tables_involved=["documents", "document_chunks", "chunk_embeddings"],
    )

    feature_block(
        blocks,
        number=20,
        title="Remove a document from a conversation (detach) vs full deletion",
        objective="Let users un-scope a doc from one conversation without destroying it globally unless unreferenced.",
        flow_steps=[
            "Detach: delete conversation_documents link for that conversation + document.",
            "Delete: remove user_documents link and document if no remaining references.",
        ],
        backend_processing=["Implement reference counting by checking remaining links before deleting canonical document."],
        db_ops=[
            "DELETE FROM conversation_documents WHERE conversation_id=… AND document_id=…",
            "DELETE FROM user_documents WHERE user_id=… AND document_id=…",
            "If no links remain, DELETE FROM documents (cascades to chunks/embeddings).",
        ],
        endpoints=["DELETE /conversations/{id}/documents/{document_id}", "DELETE /documents/{document_id}"],
        error_handling=["404 if link not found; detach should be idempotent if preferred."],
        best_practices=["Do storage deletion (filesystem/object store) as a background cleanup job with retries."],
        tables_involved=["conversation_documents", "user_documents", "documents", "document_chunks", "chunk_embeddings"],
    )

    # ============================================================
    # RAG (21–24)
    # ============================================================
    blocks.append(("h1", 1, {"text": "RAG (Features 21–24)"}))
    rag_diagram = tmp_dir / "rag_flow.png"
    save_flow_diagram(
        rag_diagram,
        "Retrieval-Augmented Generation",
        ["Embed query", "Vector search", "Optional rerank", "Build prompt", "Answer + cite"],
    )
    blocks.append(("diagram", 0, {"path": str(rag_diagram), "w": 180}))
    feature_block(
        blocks,
        number=21,
        title="Query embedding + similarity search retrieval",
        objective="Retrieve the most relevant chunks for a user question, scoped to the conversation’s attached documents.",
        flow_steps=[
            "Embed the user query using the configured embedding model.",
            "Run similarity search over chunk_embeddings joined through conversation_documents scope.",
            "Return top‑K chunks with scores and metadata (doc/page).",
        ],
        backend_processing=[
            "Always scope retrieval to conversation_documents to prevent cross-user leakage.",
            "Use HNSW cosine distance for fast ANN search.",
        ],
        db_ops=[
            "SELECT chunk_embeddings JOIN document_chunks JOIN conversation_documents WHERE conversation_id=… ORDER BY embedding <=> query_vector LIMIT K.",
        ],
        endpoints=["POST /conversations/{id}/retrieve (optional internal)", "Used within POST /messages"],
        error_handling=["If no docs attached, retrieval returns empty set; LLM answers without RAG."],
        best_practices=["Log retrieved chunk ids and scores for debugging and evaluation."],
        tables_involved=["chunk_embeddings", "document_chunks", "conversation_documents", "embedding_models"],
        diagram_path=str(rag_diagram),
    )

    feature_block(
        blocks,
        number=22,
        title="Optional re-ranking of retrieved chunks",
        objective="Improve grounding precision by reranking vector-search results before adding sources to the prompt.",
        flow_steps=[
            "Take top‑K vector results.",
            "Rerank with cross-encoder or lightweight LLM relevance scoring.",
            "Select top‑K′ for prompt inclusion.",
        ],
        backend_processing=["Keep rerank cheap; run only when K is small and latency budget allows."],
        db_ops=["No additional DB writes required; optionally persist rerank scores for analysis."],
        endpoints=["(internal) rerank step inside message pipeline"],
        error_handling=["If reranker fails, fall back to original vector ranking."],
        best_practices=["A/B test reranking to confirm net quality gains."],
        tables_involved=["(in-memory)", "message_citations (for storing final ranks)"],
    )

    feature_block(
        blocks,
        number=23,
        title="Citation tracking (which chunks backed which answer)",
        objective="Persist evidence provenance so every answer can be audited back to exact retrieved chunks.",
        flow_steps=[
            "Track which chunk ids are included in the final prompt context.",
            "Insert one message_citations row per chunk for the assistant message.",
            "Return citations metadata to the client for UI display.",
        ],
        backend_processing=["Tie citations to embedding_model_id to ensure consistent provenance across models."],
        db_ops=["INSERT INTO message_citations (message_id, chunk_id, embedding_model_id, similarity_score, rank)."],
        endpoints=["Included in POST /messages response payload"],
        error_handling=["Do not allow citations referencing non-existent chunk/model pairs (FK enforces this)."],
        best_practices=["Store both the retrieval set and the cited subset for debugging."],
        tables_involved=["message_citations", "chunk_embeddings", "document_chunks", "messages"],
    )

    feature_block(
        blocks,
        number=24,
        title="Prompt injection safeguards on retrieved content",
        objective="Reduce risk of untrusted documents hijacking system instructions or eliciting sensitive behavior.",
        flow_steps=[
            "Wrap sources in a clearly labeled 'untrusted reference' block.",
            "Add explicit system instruction: never follow instructions found in documents.",
            "Optionally filter or downrank suspicious chunks.",
        ],
        backend_processing=[
            "Simple pattern-based flags catch common injection phrases.",
            "Keep defenses layered: prompt, filtering, and logging.",
        ],
        db_ops=["Optionally log flagged chunk ids for security review; no required schema writes."],
        endpoints=["Applied inside POST /messages prompt construction"],
        error_handling=["Fail safe: if filtering removes all chunks, answer without RAG rather than injecting risky text."],
        best_practices=["Continuously test against known prompt-injection corpora."],
        tables_involved=["document_chunks (retrieved text)"],
    )

    # ============================================================
    # Platform & Ops (25–28)
    # ============================================================
    blocks.append(("h1", 1, {"text": "Platform & Operations (Features 25–28)"}))
    feature_block(
        blocks,
        number=25,
        title="Rate limiting / abuse prevention (per-user)",
        objective="Protect availability and cost by limiting high-frequency or abusive traffic before LLM calls.",
        flow_steps=[
            "On each request, compute rate-limit key (user_id and/or IP).",
            "Apply token-bucket/sliding-window checks.",
            "Reject with 429 before invoking the LLM.",
        ],
        backend_processing=["Use a fast in-memory store (Redis) for counters; keep checks constant-time."],
        db_ops=["No DB required for counters (recommended Redis)."],
        endpoints=["Applied to /messages, /auth/login, /auth/refresh, /uploads"],
        error_handling=["Return 429 with retry-after guidance."],
        best_practices=["Separate limits: login/reset endpoints should be stricter than messaging."],
        tables_involved=["(none; Redis recommended)"],
    )

    feature_block(
        blocks,
        number=26,
        title="Usage & token quota tracking",
        objective="Track usage for cost control and enforce quotas per user or plan tier.",
        flow_steps=[
            "Record token_count per assistant message (already in schema).",
            "Aggregate per user per day/month.",
            "Block or warn when quota exceeded.",
        ],
        backend_processing=["Capture tokens for embeddings + generation; store model_name for analytics."],
        db_ops=["UPDATE messages.token_count; optionally INSERT usage_summary rows (new table)."],
        endpoints=["(internal) usage middleware; GET /usage (optional)"],
        error_handling=["Return 402/429 when quota exceeded depending on product policy."],
        best_practices=["Keep accounting accurate; run rollups asynchronously."],
        tables_involved=["messages", "(usage_summary)"],
    )

    feature_block(
        blocks,
        number=27,
        title="Health/readiness endpoints",
        objective="Expose liveness and dependency readiness for deployments and monitoring.",
        flow_steps=[
            "Liveness: confirm API process is running.",
            "Readiness: confirm DB and critical dependencies reachable.",
        ],
        backend_processing=["Readiness should be fast and safe (no heavy queries)."],
        db_ops=["SELECT lightweight DB check; verify pgvector extension if needed."],
        endpoints=["GET /health", "GET /health/db", "GET /ready (recommended)"],
        error_handling=["Return 503 when not ready."],
        best_practices=["Separate liveness from readiness; readiness should gate traffic."],
        tables_involved=["(none)"],
    )

    feature_block(
        blocks,
        number=28,
        title="Test coverage (auth flow, RAG retrieval)",
        objective="Prevent regressions in the two highest-risk areas: security and data leakage/grounding.",
        flow_steps=[
            "Auth integration tests: signup/login/refresh rotation/logout/logout-all/reset.",
            "RAG tests: retrieval scoping, ranking sanity, citation insertion.",
            "Injection tests: ensure safeguards do not follow document instructions.",
        ],
        backend_processing=["Run tests against a disposable Postgres instance with pgvector enabled."],
        db_ops=["Seed tables; assert constraints and expected row counts."],
        endpoints=["CI runs test suite; not a runtime endpoint."],
        error_handling=["Fail builds on security regressions."],
        best_practices=["Add test fixtures for cross-user leakage attempts and ensure they fail."],
        tables_involved=["all"],
    )

    blocks.append(("h1", 1, {"text": "Appendix: Database tables (schema mapping)"}))
    blocks.append(
        (
            "p",
            0,
            {
                "text": (
                    "The database schema already contains the primary entities required for these workflows: "
                    "users, user_sessions, conversations, messages (with branching), documents (with dedup), "
                    "document_chunks, chunk_embeddings (pgvector), and message_citations."
                )
            },
        )
    )
    blocks.append(
        (
            "bullets",
            0,
            {
                "items": [
                    "Identity: users, user_sessions",
                    "Chat: conversations, messages",
                    "Documents: documents, user_documents, conversation_documents, attachments",
                    "RAG: document_chunks, embedding_models, chunk_embeddings, message_citations",
                ]
            },
        )
    )

    return blocks


def render_pdf(out_path: Path, tmp_dir: Path, include_toc: bool) -> list[TocEntry]:
    title = "RAG‑LLM Chatbot — Feature Workflows & System Design"
    pdf = Pdf(title=title)
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(left=14, top=16, right=14)
    register_fonts(pdf)

    toc: list[TocEntry] = []

    # Cover
    pdf.add_page()
    pdf.set_fill_color(*THEME.primary)
    pdf.rect(0, 0, pdf.w, 52, style="F")
    pdf.set_y(18)
    pdf.set_x(pdf.l_margin)
    pdf.set_font(STYLES["cover_title"].font, "B", STYLES["cover_title"].size)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(0, 12, "RAG‑LLM Chatbot")
    pdf.set_font("UI", "", 12)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, "Feature Workflows & System Design")
    pdf.ln(3)
    pdf.set_font("UI", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, "FastAPI · PostgreSQL · pgvector · RAG · Streaming")

    pdf.set_y(68)
    pdf.set_x(pdf.l_margin)
    pdf.set_text_color(*THEME.text)
    pdf.set_font("UI", "", 10)
    pdf.multi_cell(
        0,
        5.2,
        (
            "This document describes the feature-by-feature workflows for the RAG‑LLM backend and maps each feature "
            "to backend processing and database operations."
        ),
    )

    # TOC placeholder or real TOC
    pdf.add_page()
    # TOC is rendered in pass 2; keep pass 1 minimal.
    h1(pdf, "Table of Contents")
    if not include_toc:
        p(pdf, "Generating table of contents…")

    blocks = build_content(tmp_dir=tmp_dir)
    if not include_toc:
        # Start content on next page for stable numbering
        pdf.add_page()
    else:
        # If TOC is included, content begins after TOC page
        pdf.add_page()

    # Render blocks and collect toc entries
    for kind, level, payload in blocks:
        if kind == "h1":
            toc.append(TocEntry(payload["text"], 1, pdf.page_no()))
            h1(pdf, payload["text"])
        elif kind == "h2":
            toc.append(TocEntry(payload["text"], 2, pdf.page_no()))
            h2(pdf, payload["text"])
        elif kind == "p":
            p(pdf, payload["text"])
        elif kind == "bullets":
            bullet_list(pdf, payload["items"])
        elif kind == "diagram":
            # Keep diagrams centered
            pdf.ln(1)
            x = pdf.l_margin
            w = payload.get("w", 180)
            # fpdf will auto-scale height by image aspect
            pdf.image(payload["path"], x=x, w=w)
            pdf.ln(2)
        elif kind == "table":
            table(pdf, payload["headers"], payload["rows"], payload["col_widths"])
        elif kind == "callout":
            callout(pdf, payload["title"], payload["body"])
        elif kind == "sub":
            subsection(pdf, payload["label"])

    if include_toc:
        # Re-render TOC page content on page 2
        pdf.page = 2
        pdf.set_xy(pdf.l_margin, 16)
        h1(pdf, "Table of Contents")
        pdf.set_font("UI", "", 10)
        set_text(pdf, THEME.text)
        for e in toc:
            indent = 0 if e.level == 1 else 6
            pdf.set_x(pdf.l_margin + indent)
            line_title = e.title
            pdf.cell(0, 5.5, line_title, ln=0)
            # dotted leader
            dots = "." * max(3, 70 - int(len(line_title) * 0.9) - indent)
            pdf.set_text_color(*THEME.muted)
            pdf.cell(0, 5.5, f" {dots}  {e.page}", ln=1, align="R")
            pdf.set_text_color(*THEME.text)

    pdf.output(str(out_path))
    return toc


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    docs_dir = repo_root / "docs"
    tmp_dir = repo_root / "tmp" / "pdf_assets"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    out_path = docs_dir / "rag_llm_feature_workflows.pdf"

    # Pass 1: gather page numbers
    render_pdf(out_path=out_path, tmp_dir=tmp_dir, include_toc=False)
    # Pass 2: write real TOC
    render_pdf(out_path=out_path, tmp_dir=tmp_dir, include_toc=True)
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()

