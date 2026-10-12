# Backup and restoration contract

This local database is development infrastructure. Encrypted production backups,
off-host deletion-journal replication, alerts and a measured restore rehearsal
are still release blockers. No 30-day expiry compliance is claimed.

Keep private documents until tenant deletion. The API durably records IDs,
timestamps and deletion epochs in an independent journal before committing a
tombstone. A tombstone revokes reads immediately; the leased worker purges the
original and extracted pages. Purge jobs retry without a five-attempt cutoff.
Alert on any unpurged tombstone older than 24 hours. Never put text or filenames
in deletion receipts, logs, metric labels, or job payloads.

Production operators must encrypt consistent database/object snapshots with
separately managed keys, expire every usable backup within 30 days, retain
deletion records beyond the usable backup window, and replicate the newest
journal outside the snapshot being restored. Checksums detect alteration but
do not authenticate a maliciously replaced journal. Access control, signed
receipts and proof of replication/currentness require an operational review.

Restore with the API closed: recover the database and objects, preserve the
newest independent journal, run `python scripts/reapply_deletions.py
--maintenance-confirmed`, run the purge worker, verify every deleted canary is
inaccessible and absent from objects/pages, then reopen access. A missing,
stale, or corrupt journal blocks reopening. Do not restore an old journal over
the newest deletion records. Rehearse this on a separate database; never
overwrite the active development database to simulate a restore.
