from larklab.models import DailyDigest


def trash_processed_emails(
    service, digests: list[DailyDigest], verbose: bool = False,
) -> list[str]:
    """Move processed Scholar alert emails to trash. Returns list of trashed message IDs."""
    email_ids = {p.source_email_id for d in digests for p in d.papers if p.source_email_id}

    trashed = []
    for eid in email_ids:
        try:
            if verbose:
                meta = service.users().messages().get(
                    userId="me", id=eid, format="metadata", metadataHeaders=["Subject"],
                ).execute()
                subject = next(
                    (h["value"] for h in meta["payload"]["headers"] if h["name"] == "Subject"),
                    "(no subject)",
                )
                print(f"  Trashing: {subject}")
            service.users().messages().trash(userId="me", id=eid).execute()
            trashed.append(eid)
        except Exception as e:
            print(f"  Failed to trash email {eid}: {e}")

    return trashed
