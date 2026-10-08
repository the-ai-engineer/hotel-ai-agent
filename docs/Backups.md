# Database backups

The hotel database is the Cloud SQL instance `hotel-postgres` in
`personal-infrastructure-505708` (`europe-west2`).

## Policy

- Cloud SQL automated backups run daily in a four-hour window starting 19:00 UTC
  (03:00 `Asia/Makassar`).
- The last 7 backups are kept. Older ones are deleted by Cloud SQL.
- Point-in-time recovery is off. A restore can lose up to one day of writes.
- Sessions are deleted about 30 days after creation by the daily maintenance
  job. Backups then hold them for about 7 more days, so guest data normally
  lasts about 38 days. This assumes daily backups succeed: retention counts
  backups, not days, so failed windows make the kept backups older.
- On-demand backups are not removed by retention. Delete them after use, or
  they keep guest data indefinitely.

Pass `--project personal-infrastructure-505708` on every command. The local
gcloud default project may point elsewhere. Run this first in each shell:

```bash
P=personal-infrastructure-505708
```

## Check backups

```bash
gcloud sql instances describe hotel-postgres --project $P \
  --format="yaml(settings.backupConfiguration)"
gcloud sql backups list --instance hotel-postgres --project $P
```

## Alert

`infra/hotel-postgres-backup-alert.yaml` emails the `hotel-alerts` channel when
a backup window ends without success (`STATUS_FAILED` or `STATUS_SKIPPED`).
Single retried attempts do not alert. It does not fire if backups are disabled
or a window writes no log, so check `describe` after instance changes.

When it fires, look for a conflicting operation (export, import, restart or
maintenance) in the backup window, then take an on-demand backup (delete it once a daily backup succeeds):

```bash
gcloud sql operations list --instance hotel-postgres --project $P --limit 20
gcloud sql backups create --instance hotel-postgres --project $P
```

## Restore test

Restore into a temporary instance. Never restore over `hotel-postgres` unless
recovering from data loss, because that replaces all current data.

1. Pick a successful backup ID:

   ```bash
   gcloud sql backups list --instance hotel-postgres --project $P
   ```

2. Create a temporary instance and restore into it (costs a few pence per hour):

   ```bash
   gcloud sql instances create hotel-postgres-restore-test --project $P \
     --database-version POSTGRES_17 --edition enterprise --tier db-f1-micro \
     --region europe-west2 --no-backup
   gcloud sql backups restore BACKUP_ID --project $P \
     --backup-instance hotel-postgres --restore-instance hotel-postgres-restore-test
   ```

3. Compare row counts on both instances. Connect with `cloud-sql-proxy` and the
   database user from Secret Manager; the restored instance keeps the source
   users. Writes after the backup time may make live counts higher.

   ```sql
   SELECT 'documents', count(*) FROM documents
   UNION ALL SELECT 'villas', count(*) FROM villas
   UNION ALL SELECT 'inventory_days', count(*) FROM inventory_days
   UNION ALL SELECT 'guest_sessions', count(*) FROM guest_sessions
   UNION ALL SELECT 'turns', count(*) FROM turns
   UNION ALL SELECT 'bookings', count(*) FROM bookings
   UNION ALL SELECT 'hotel_requests', count(*) FROM hotel_requests;
   ```

4. Delete the temporary instance:

   ```bash
   gcloud sql instances delete hotel-postgres-restore-test --project $P
   ```

## Recover from data loss

Restoring onto `hotel-postgres` overwrites it and restarts the instance. Pause
application traffic, take an on-demand backup of the current state so nothing
surviving is lost, then restore with `--restore-instance hotel-postgres`. Run the restore-test row counts and
the deployed smoke tests before reopening traffic. Delete the safety backup once it is no longer needed.
