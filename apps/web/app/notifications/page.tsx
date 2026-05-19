"use client";

import Link from "next/link";

import { OperatorNotificationSurface } from "../../components/OperatorNotificationSurface";
import { PageShell } from "../../components/ui/PageShell";
import { PageHeader } from "../../components/shell/PageHeader";

export default function NotificationsPage() {
  return (
    <PageShell>
      <PageHeader
        title="Notifications"
        subtitle="Unified notification lane for unread and recent alert activity with direct links to execution and workflow actions."
        actions={
          <Link href="/alerts" style={{ color: "var(--state-info)", textDecoration: "none", fontWeight: 700, fontSize: 12 }}>
            Open alert rules →
          </Link>
        }
      />
      <OperatorNotificationSurface title="Notifications" maxItems={20} />
    </PageShell>
  );
}
