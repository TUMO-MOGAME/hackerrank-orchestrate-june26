"use client";

import { useEffect, useState } from "react";
import {
  type Notification,
  markNotificationsRead,
  notificationsFor,
} from "../lib/claims";

export function NotificationBell({ email, isAdmin }: { email: string; isAdmin: boolean }) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState<Notification[]>([]);

  useEffect(() => {
    setNotes(notificationsFor(email, isAdmin));
    const t = setInterval(() => setNotes(notificationsFor(email, isAdmin)), 2500);
    return () => clearInterval(t);
  }, [email, isAdmin]);

  const unread = notes.filter((n) => !n.read).length;

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && unread) {
      markNotificationsRead(email, isAdmin);
      setTimeout(() => setNotes(notificationsFor(email, isAdmin)), 50);
    }
  }

  return (
    <div className="bell">
      <button className="bell__btn" onClick={toggle} aria-label="Notifications" type="button">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6Z M10 20a2 2 0 0 0 4 0"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {unread > 0 && <span className="bell__badge">{unread}</span>}
      </button>
      {open && (
        <div className="bell__panel">
          <div className="bell__head mono">Notifications</div>
          {notes.length === 0 ? (
            <div className="muted" style={{ padding: 16, fontSize: "0.86rem" }}>
              Nothing yet.
            </div>
          ) : (
            notes.slice(0, 12).map((n) => (
              <div key={n.id} className="bell__item">
                <span className="dot" style={{ color: n.read ? "var(--line-strong)" : "var(--ember)" }} />
                <div>
                  <div style={{ fontSize: "0.86rem" }}>{n.message}</div>
                  <div className="muted mono" style={{ fontSize: "0.68rem" }}>
                    {n.claimId}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
