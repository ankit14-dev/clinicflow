#!/usr/bin/env bash
# Fill a fresh ClinicFlow install with demo patients and appointments through the public API.
#   ./scripts/seed-demo.sh                       # docker compose (http://localhost:3000)
#   ./scripts/seed-demo.sh http://<ingress-host> # Kubernetes
set -euo pipefail
URL="${1:-http://localhost:3000}"
api() { curl -fsS -X "$1" "$URL/api/$2" -H 'Content-Type: application/json' ${3:+-d "$3"}; }
id() { python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])'; }
# ISO-8601 UTC timestamp: today/tomorrow (+N days) at HH:MM clinic time (IST, UTC+5:30)
slot() { python3 -c "
import sys; from datetime import datetime, timedelta, timezone
ist = timezone(timedelta(hours=5, minutes=30))
d = datetime.now(ist).replace(hour=int(sys.argv[2]), minute=int(sys.argv[3]), second=0, microsecond=0) + timedelta(days=int(sys.argv[1]))
print(d.astimezone(timezone.utc).isoformat())" "$@"; }

mapfile -t DOCTORS < <(api GET doctors | python3 -c 'import sys, json; [print(d["id"]) for d in json.load(sys.stdin)]')
[ "${#DOCTORS[@]}" -ge 3 ] || { echo "need at least 3 doctors (the Alembic seed adds 5)"; exit 1; }

declare -a PATIENTS
while IFS='|' read -r name phone email dob; do
  PATIENTS+=("$(api POST patients "{\"full_name\":\"$name\",\"phone\":\"$phone\",\"email\":\"$email\",\"date_of_birth\":\"$dob\"}" | id)")
done <<'LIST'
Asha Verma|+91 98765 43210|asha.verma@example.com|1990-04-12
Rahul Sharma|+91 91234 56780|rahul.s@example.com|1985-11-02
Priya Menon|+91 99887 76655|priya.menon@example.com|2016-07-21
Karan Singh|+91 90000 11122|karan.singh@example.com|1972-02-15
Neha Joshi|+91 98111 22233|neha.j@example.com|1998-09-30
Arjun Das|+91 97222 33344|arjun.das@example.com|1964-06-08
LIST

book() { # patient doctor days hh mm reason
  local when; when=$(slot "$3" "$4" "$5")
  # skip silently if the slot is already in the past (seeding late in the day)
  api POST appointments "{\"patient_id\":$1,\"doctor_id\":$2,\"scheduled_at\":\"$when\",\"reason\":\"$6\"}" 2>/dev/null | id || true
}
book "${PATIENTS[0]}" "${DOCTORS[0]}" 0 21 0 "Fever and sore throat"
book "${PATIENTS[1]}" "${DOCTORS[1]}" 0 22 0 "ECG follow-up"
book "${PATIENTS[2]}" "${DOCTORS[2]}" 0 22 30 "Vaccination"
book "${PATIENTS[3]}" "${DOCTORS[1]}" 1 10 0 "Chest pain review"
book "${PATIENTS[4]}" "${DOCTORS[3]}" 1 11 30 "Skin allergy"
book "${PATIENTS[5]}" "${DOCTORS[4]}" 2 9 30 "Knee pain"
book "${PATIENTS[0]}" "${DOCTORS[0]}" 3 12 0 "Blood test results"
book "${PATIENTS[1]}" "${DOCTORS[2]}" 4 16 0 "Child's annual check-up"
echo "Seeded ${#PATIENTS[@]} patients. Stats:"; api GET stats; echo
