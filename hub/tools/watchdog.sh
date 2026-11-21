#!/bin/bash
# Go-go watchdog: run every 30 s by launchd (com.bb.gogo.watchdog). Checks the hub, the caregiver page,
# the glasses and Messages, fixes what it can, and logs to hub/data/watchdog.log.
# A macOS notification appears only when something goes wrong or comes back.
#   GLASSES_IP   the glasses' Wi-Fi address (default 10.3.195.33)
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
DIR="$(cd "$(dirname "$0")/.." && pwd)"          # hub/
LOG="$DIR/data/watchdog.log"
STATE="$DIR/data/watchdog.state"
GLASSES_IP="${GLASSES_IP:-10.3.195.33}"
U="$(id -u)"
now() { date "+%H:%M:%S"; }
log() { echo "$(now) $*" >> "$LOG"; }
notify() { osascript -e "display notification \"$1\" with title \"Go-go watchdog\"" >/dev/null 2>&1; }
prev="$(cat "$STATE" 2>/dev/null)"
problems=""

# 1. hub answers
if ! curl --noproxy '*' -s -m 4 http://127.0.0.1:9100/api/state -o /tmp/gogo_state.json; then
  problems="$problems hub"
  log "hub not answering: restarting"
  launchctl kickstart -k "gui/$U/com.bb.gogo.hub"
fi

# 2. caregiver page answers
if ! curl -s -m 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:9300/dashboard/ | grep -q 200; then
  problems="$problems caregiver"
  log "caregiver page down: restarting"
  launchctl kickstart -k "gui/$U/com.bb.gogo.care"
fi

# 3. glasses connected to the hub (skip if the hub itself is down)
if [[ "$problems" != *hub* ]] && ! grep -q '"glasses":true' /tmp/gogo_state.json 2>/dev/null; then
  problems="$problems glasses"
  MAC_IP="$(ipconfig getifaddr en0)"
  misses=$(( $(cat "$DIR/data/watchdog.glasses" 2>/dev/null || echo 0) + 1 )); echo $misses > "$DIR/data/watchdog.glasses"
  log "glasses not connected (Mac $MAC_IP, glasses $GLASSES_IP, check $misses)"
fi
# The app reconnects by itself after a Wi-Fi blip; only step in after a minute (2 checks) without it.
if [[ "$problems" == *glasses* ]] && [ "${misses:-0}" -ge 2 ]; then
  # Over USB if plugged in, else over Wi-Fi adb: point the app at the Mac's current address and restart it.
  adb connect "$GLASSES_IP:5555" >/dev/null 2>&1
  DEV="$(adb devices | awk 'NR>1 && $2=="device"{print $1}' | grep -v ':' | head -1)"
  [ -z "$DEV" ] && DEV="$(adb devices | awk 'NR>1 && $2=="device"{print $1}' | head -1)"
  if [ -n "$DEV" ]; then
    adb -s "$DEV" reverse tcp:9100 tcp:9100 >/dev/null 2>&1
    adb -s "$DEV" shell am force-stop com.bb.lucia >/dev/null 2>&1
    adb -s "$DEV" shell am start -n com.bb.lucia/.MainActivity \
      --es hub "ws://$MAC_IP:9100/ws/glasses,ws://127.0.0.1:9100/ws/glasses" >/dev/null 2>&1
    log "  restarted the glasses app via $DEV"
  else
    ping -c 1 -t 2 "$GLASSES_IP" >/dev/null 2>&1 && log "  glasses answer ping but adb is off: plug in USB once" \
                                                   || log "  glasses not on the network (off, asleep or Wi-Fi dropped)"
  fi
fi

[[ "$problems" != *glasses* ]] && echo 0 > "$DIR/data/watchdog.glasses"

# 4. Messages running (caregiver texts go out through it)
if ! pgrep -x Messages >/dev/null; then
  problems="$problems messages"
  log "Messages not running: opening it"
  open -g -a Messages
fi

problems="${problems# }"
if [ "$problems" != "$prev" ]; then
  if [ -n "$problems" ]; then notify "Problem: $problems. Fixing it."; else notify "All good again: hub, caregiver page, glasses, Messages."; log "all good"; fi
fi
echo "$problems" > "$STATE"
