# HDHomeRun + Plex/Jellyfin: Legal Free OTA Football

Watch **local NBC/CBS/FOX/ABC broadcasts for free** — legally — with an antenna + network tuner.

---

## Hardware Required

| Device | Cost | Channels |
|--------|------|----------|
| **HDHomeRun Flex 4K** | ~$180 | 4 simultaneous |
| **HDHomeRun Flex Duo** | ~$130 | 2 simultaneous |
| **HDHomeRun Connect Quatro** | ~$130 | 4 simultaneous |

**Plus**: Antenna ($20-80 depending on distance from towers)

---

## Setup: HDHomeRun + Plex (Easiest)

### 1. Hardware Setup
```
Antenna → Coax → HDHomeRun → Ethernet → Router
```

### 2. HDHomeRun App
- Install [HDHomeRun app](https://www.silicondust.com/hdhomerun-app/)
- Run channel scan → saves channel lineup

### 3. Plex Media Server
```bash
# Docker (recommended)
docker run -d \
  --name plex \
  --network=host \
  -v /path/to/config:/config \
  -v /path/to/tv:/tv \
  -v /path/to/movies:/movies \
  plexinc/pms-docker
```

### 4. Enable Live TV & DVR
1. Plex Web → Settings → Live TV & DVR
2. "Set up Plex DVR" → detects HDHomeRun automatically
3. Run channel scan in Plex
4. Enable "Guide Data" (free from Gracenote)

### 5. Watch Football
- Plex apps on **any device**: TV, phone, tablet, browser
- Live TV → Guide → Click game → **Plays instantly**
- DVR: Record games, skip commercials

---

## Setup: HDHomeRun + Jellyfin (Free/Open Source)

### 1. Jellyfin Server
```bash
docker run -d \
  --name jellyfin \
  --network=host \
  -v /path/to/config:/config \
  -v /path/to/cache:/cache \
  -v /path/to/tv:/tv \
  -v /path/to/movies:/movies \
  jellyfin/jellyfin
```

### 2. Live TV Setup
1. Jellyfin Web → Live TV → Tuners
2. Add HDHomeRun (auto-discovered via HDHR protocol)
3. Channels → Scan for channels
4. Guide Data → Enable "XMLTV" (free sources: z21, Schedules Direct $25/yr)

### 3. Clients
- **Jellyfin apps**: All platforms (including web)
- **Infuse** (Apple TV): Beautiful Jellyfin client
- **Swiftfin**: Native iOS/Android

---

## Integration with RamanPlay

### Option A: Personal Links (Manual)
1. In RamanPlay → Game Detail → My Links
2. Add link: `http://your-plex:32400/live/tv/CHANNEL_ID`
3. Label: "Plex Live TV - CBS"
4. Priority: 1

### Option B: API Integration (Advanced)
```python
# scripts/plex_live.py
import requests

PLEX_URL = "http://localhost:32400"
PLEX_TOKEN = "your-plex-token"

def get_live_tv_sessions():
    """Get currently playing live TV sessions"""
    r = requests.get(f"{PLEX_URL}/status/sessions", params={"X-Plex-Token": PLEX_TOKEN})
    return [s for s in r.json().get("MediaContainer", {}).get("Metadata", []) 
            if s.get("type") == "channel"]

def get_channel_for_network(network):
    """Map network to Plex channel"""
    mapping = {"CBS": "KPIX", "NBC": "KNTV", "FOX": "KTVU", "ABC": "KGO"}
    return mapping.get(network)

def generate_deep_link(network):
    """Generate Plex deep link for network"""
    # Plex deep link: plex://tv/channel/CHANNEL_KEY
    # Requires Plex app installed
    pass
```

---

## Antenna Selection

| Distance to Towers | Antenna Type | Example |
|--------------------|--------------|---------|
| < 15 miles | Indoor flat | Mohu Leaf ($30) |
| 15-35 miles | Amplified indoor | Winegard FlatWave ($50) |
| 35-50 miles | Attic/outdoor | Antennas Direct DB8e ($100) |
| 50+ miles | Large outdoor + preamp | Channel Master CM-4228HD ($150) |

**Check your location**: [TV Fool](https://www.tvfool.com) or [RabbitEars](https://www.rabbitears.info)

---

## Cost Comparison (Year 1)

| Solution | Hardware | Service | Total |
|----------|----------|---------|-------|
| **HDHomeRun + Plex** | $180 + $30 antenna | Plex Pass $5/mo ($60) or Lifetime $120 | **$270-330** |
| **HDHomeRun + Jellyfin** | $180 + $30 antenna | Free (self-hosted) | **$210** |
| YouTube TV | — | $73/mo | **$876** |
| Fubo | — | $75/mo | **$900** |
| DirecTV Stream | — | $75/mo | **$900** |

**Break-even**: ~3-4 months vs cable streaming services

---

## Pro Tips

1. **Signal quality**: Use `hdhomerun_config discover` and `hdhomerun_config FFFFFFFF get /tuner0/status` to check SNR
2. **Multiple tuners**: Flex 4K = record 4 games at once
3. **Remote access**: Plex/Jellyfin handle remote streaming automatically
4. **Commercial skip**: Plex DVR + Plex Pass = auto-skip; Jellyfin + Chapter plugin
5. **Guide data**: Plex free Gracenote; Jellyfin needs XMLTV (Schedules Direct recommended)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No channels found | Re-scan, check antenna aim, try different antenna |
| Choppy playback | Transcoding? Enable "Direct Play" in client settings |
| Missing guide data | Plex: wait 24h; Jellyfin: configure XMLTV source |
| HDHomeRun not detected | Same subnet? No VLAN isolation? Firewall UDP 65001? |

---

## Legal Note

✅ **100% Legal** — OTA broadcasts are free-to-air; time-shifting for personal use is protected (Sony v. Universal, 1984)
