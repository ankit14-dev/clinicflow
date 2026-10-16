#!/usr/bin/env bash
# Steady, realistic traffic through the Ingress so Grafana panels have data (reads, bookings, 404s, conflicts).
#   ./scripts/traffic.sh http://<ingress-host> [seconds]
set -uo pipefail
URL="${1:?usage: $0 <base-url> [seconds]}"; DURATION="${2:-300}"
end=$((SECONDS + DURATION))
doctor=$(curl -fsS "$URL/api/doctors?active=true" | python3 -c 'import sys,json; print(json.load(sys.stdin)[0]["id"])')
patient=$(curl -fsS "$URL/api/patients" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')
while [ $SECONDS -lt $end ]; do
  for _ in 1 2 3 4 5; do curl -s -o /dev/null "$URL/api/appointments" & done
  curl -s -o /dev/null "$URL/api/stats"
  curl -s -o /dev/null "$URL/api/appointments/999999"        # 404
  if [ -n "$patient" ]; then                                   # book a random future slot (some will conflict -> 409)
    when=$(python3 -c "import random; from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(days=random.randint(5,30),minutes=15*random.randint(0,40))).replace(second=0,microsecond=0).isoformat())")
    curl -s -o /dev/null -X POST "$URL/api/appointments" -H 'Content-Type: application/json' \
      -d "{\"patient_id\":$patient,\"doctor_id\":$doctor,\"scheduled_at\":\"$when\",\"reason\":\"Traffic generator visit\"}"
  fi
  wait; sleep 1
done
