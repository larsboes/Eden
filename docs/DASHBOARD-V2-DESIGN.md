# EDEN Dashboard V2 — Design Document

> Design session output. The merged K8s + Agriculture visualization concept.
> ArgoCD resource tree as primary view, dome as deep-dive, Hubble-style resource flow.

---

## The Core Insight

Every hackathon team will build "a dashboard with sensor readings." We're building **ArgoCD for agriculture** — a system that doesn't just DISPLAY data, it shows the **architecture of autonomous decision-making**.

An AWS engineer looks at it and sees K8s. A Syngenta scientist looks at it and sees plants growing. A design judge looks at it and sees something they've never seen before. Everyone's right.

---

## The Full K8s to EDEN Visual Map

### The Resource Tree (ArgoCD-inspired)

```
          CLUSTER              NODES              PODS                PROBES + SIDECARS
        +------------+     +--------------+   +--------------+    +-------------------+
        |            |     |              |   |              |    | Liveness: 30s     |
        | EDEN       |---->| Node:PROTEIN |-->| Pod:Soybean  |--->| Readiness: 30d    |
        | Cluster    |     |              |   |   plant  91% |    | Sidecar: Lentil   |
        |            |     |              |-->| Pod:Lentil   |    +-------------------+
        |            |     +--------------+   |   plant  88% |
        |            |     +--------------+   +--------------+
        |            |---->| Node:CARB    |--> ...
        |            |     +--------------+
        |            |     +--------------+
        |            |---->| Node:VITAMIN |--> ...
        |            |     +--------------+
        |            |     +--------------+
        |            |---->| Node:SUPPORT |--> ...
        +------------+     +--------------+
```

Inside each Pod box, a PlantSVG is actually growing. The boxes aren't dead data. They're alive.

### Every K8s Concept Visualized

| K8s Concept | EDEN Mapping | How It's VISIBLE in the UI |
|---|---|---|
| **Cluster** | Greenhouse dome | Left column: EDEN root box with aggregate health |
| **Node** | Grow zone | Middle column: zone boxes with env readings |
| **Pod** | Individual crop | Inside node boxes: crop cards with mini PlantSVGs |
| **Container** | Plant unit | The PlantSVG itself (stem, leaves, fruit) |
| **Sidecar** | Companion plant | Small icon attached to pod: `tomato--basil` (Basil sidecar) |
| **Liveness Probe** | "Is it alive?" | Green dot pulsing every 30s on each pod |
| **Readiness Probe** | "Is it harvestable?" | Progress ring around pod (empty = not ready, full = harvest) |
| **HPA Autoscaler** | Nutritional gap trigger | Event: "HPA: Iron deficit -> scaling spinach +2 pods" |
| **CrashLoopBackOff** | Seed fails 3x | Pod status: `CrashLoop: 2/3 attempts` (retry with diff conditions) |
| **Rolling Update** | Crop rotation | Timeline shows: old harvest fading out, new planting fading in |
| **Canary Deployment** | Virtual Lab | Strategy card: `Canary: 3% loss (sim) -> PROMOTE?` |
| **ResourceQuota** | Water/nutrient budget | Small gauge inside each node: `water 1.75/3.0 L/sol` |
| **PodDisruptionBudget** | Max offline crops | Cluster box: `PDB: max 30% unavail, current 12%` |
| **NetworkPolicy** | Condition Zebra | During crisis: `NetworkPolicy ACTIVE: zone isolation` |
| **Admission Controller** | Flight Rules Engine | Event: `AdmissionCtrl: FR-CME-001 ADMITTED` |
| **ConfigMap** | Growth parameters | Inside pod detail: `ConfigMap: pH 6.2, EC 1.8, DLI 17` |
| **DaemonSet** | Env monitoring | Status line: `DaemonSet: 4/4 sensors reporting` |
| **Ingress** | External data sources | Flow diagram: `Ingress: Syngenta KB, DONKI, InSight` |
| **Reconciliation** | Desired vs actual | Cluster status: `Synced` or `OutOfSync` with diff |

---

## The Full Page Layout — Nominal State

```
+----------------------------------------------------------------------+
| EDEN   Sol 247  14:24:09   Reconciled   87 rules  DaemonSet 4/4  moon|
+----------------------------------------------------------------------+
|                                                                      |
| +- AGENT STREAM ---------------------------------------------------+ |
| | FLORA  14:19 -- Sol 247. Soybean BBCH 65. Companion synergy...   | |
| +------------------------------------------------------------------+ |
|                                                                      |
| +- CLUSTER TREE --------------------------------------------------+  |
| |                                                                  |  |
| |  +------------+       +-------------------------------------+   |  |
| |  | EDEN       |       | beans PROTEIN  Node:A        * 90% |   |  |
| |  |            |       |                                     |   |  |
| |  | Reconciled |------>|  +---------+  +---------+           |   |  |
| |  |  Synced    |       |  | plant   |  | plant   |           |   |  |
| |  |            |       |  | Soybean |  | Lentil  |  <-> comp |   |  |
| |  | Nodes: 4   |       |  | 91% *   |  | 88% *   |           |   |  |
| |  | Pods: 8    |       |  | BBCH 65 |  | BBCH 71 |           |   |  |
| |  | Rules: 87  |       |  | half 30d|  | half 25d| readiness |   |  |
| |  |            |       |  +---------+  +---------+           |   |  |
| |  | Health     |       |  water 1.75 L/sol   VPD 0.95       |   |  |
| |  | ####_ 92%  |       +-------------------------------------+   |  |
| |  |            |       +-------------------------------------+   |  |
| |  | PDB:       |       | wheat CARB  Node:B            * 92%|   |  |
| |  | 0/8 unav.  |------>|                                     |   |  |
| |  | Budget: 30%|       |  +---------+  +---------+           |   |  |
| |  |            |       |  | plant   |  | plant   |           |   |  |
| |  | Reconcile: |       |  | Potato  |  | Wheat   |           |   |  |
| |  | 30s ago    |       |  | 94% *   |  | 90% o   |           |   |  |
| |  |            |       |  | BBCH 45 |  | BBCH 55 |           |   |  |
| |  | Sol 247    |       |  +---------+  +---------+           |   |  |
| |  | ---------- |       |  water 2.35 L/sol   VPD 1.12       |   |  |
| |  | 450        |       +-------------------------------------+   |  |
| |  |            |       +-------------------------------------+   |  |
| |  |            |       | tomato VITAMIN  Node:C        o 91%|   |  |
| |  |            |------>|                                     |   |  |
| |  |            |       |  +---------+  +---------+           |   |  |
| |  |            |       |  | plant   |  | plant   |           |   |  |
| |  |            |       |  | Tomato  |  | Spinach |           |   |  |
| |  |            |       |  | 86% *   |  | 96% *   |           |   |  |
| |  |            |       |  | BBCH 73 |  | BBCH 41 |           |   |  |
| |  |            |       |  +---------+  +---------+  basil sc |   |  |
| |  |            |       |  water 2.0 L/sol   VPD 0.88 hum:42%|   |  |
| |  |            |       +-------------------------------------+   |  |
| |  |            |       +-------------------------------------+   |  |
| |  |            |------>| herb SUPPORT  Node:D          * 94% |   |  |
| |  |            |       |  +---------+  +---------+           |   |  |
| |  |            |       |  | Basil   |  | Microgrn|           |   |  |
| |  |            |       |  | 94% *   |  | 95% *   |           |   |  |
| |  |            |       |  | BBCH 30 |  | BBCH 10 |           |   |  |
| |  +------------+       |  +---------+  +---------+           |   |  |
| |                        +-------------------------------------+   |  |
| |                                                                  |  |
| +------------------------------------------------------------------+  |
|                                                                      |
| +- RESOURCE FLOW (Hubble) ----------------------------------------+  |
| |                                                                  |  |
| |   +--------+     +--------+     +--------+     +-------------+  |  |
| |   |* SOLAR |---->|z POWER |---->|drop DESAL|-->|plant IRRIGATE|  |  |
| |   | 4.2 kW |     | Grid   |     | 120L/s |     | 4 zones     |  |  |
| |   | 100%   |     | 78%    |     |        |     +------+------+  |  |
| |   +--------+     +---+----+     +--------+            |         |  |
| |                      |                                |         |  |
| |                 +----+----+                    +------+------+  |  |
| |                 | LIGHTS  |                    | HARVEST     |  |  |
| |                 | HEAT    |                    | kcal + vit  |  |  |
| |                 | SHIELD  |                    +------+------+  |  |
| |                 | BATTERY |                           |         |  |
| |                 | 78%     |                    +------+------+  |  |
| |                 +---------+                    | CREW        |  |  |
| |                                                | 4 astronauts|  |  |
| |   +----------------------+                     | VitC: 133%  |  |  |
| |   | INGRESS              |                     | Iron: 112%  |  |  |
| |   | Syngenta KB / DONKI  |                     | O2: 14.2%   |  |  |
| |   | InSight / NASA POWER |                     +-------------+  |  |
| |   +----------------------+                                      |  |
| +------------------------------------------------------------------+  |
|                                                                      |
| +- EVENTS (kubectl get events) -----------------------------------+  |
| | AGE  TYPE     REASON           OBJECT             MESSAGE       |  |
| | ----------------------------------------------------------------|  |
| | 10s  Normal   LivenessProbe    pod/soybean        Sensors OK    |  |
| | 30s  Normal   Reconciled       cluster/eden       Synced        |  |
| | 1m   Normal   CronJob          dreamer/nightly    4,217 sims    |  |
| | 2m   Warning  VPDDrift         node/vitamin       0.88 < target |  |
| | 5m   Normal   AdmissionCtrl    rule/FR-H-003      Armed: VPD    |  |
| | 8m   Normal   RollingUpdate    node/vitamin       Spinach cy 5  |  |
| +------------------------------------------------------------------+  |
|                                                                      |
| +===========================Sol 247/450============================+  |
|                                                                      |
| [astronaut Crew] [clipboard Rules: 87] [scroll Memory] [robot Council]|
|                                                                      |
| ~~~~~~~~~~~~~~~~~ Mars terrain gradient ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ |
+----------------------------------------------------------------------+
```

---

## Crisis Mode — The Tree Under Attack

When CME hits, the entire tree transforms. This IS the demo climax:

```
+----------------------------------------------------------------------+
| EDEN   Sol 249  CRISIS      WARNING DEGRADED   89 rules  Shields ON  |
+----------------------------------------------------------------------+
| WARNING CME-2026-0315  1,247 km/s  DONKI           02:14:33          |
+----------------------------------------------------------------------+
| SENTINEL  14:24 -- CME IMPACT. Radiation 263 uSv/hr. Shields ON.    |
+----------------------------------------------------------------------+
|                                                                      |
|  +------------+       +--- * GREEN ----------------------------+     |
|  | EDEN       |       | beans PROTEIN  Node:A            * 90%|     |
|  |            |------>|  +---------+  +---------+              |     |
|  | WARNING    |       |  | Soy 91  |  | Len 88  |              |     |
|  | DEGRADED   |       |  | * OK    |  | * OK    |              |     |
|  |            |       |  +---------+  +---------+              |     |
|  | CME Active |       +----------------------------------------+     |
|  |            |       +--- RED RED --------------------------------+ |
|  | Strategy C |       | wheat CARB  Node:B          RED TRIAGE     | |
|  |  PROMOTED  |------>|  +---------+  +---------+                  | |
|  |            | (red) |  | Pot 94  |  | Wht 72  | <- stress       | |
|  | PDB:       |       |  | * OK    |  | RED RED | animations      | |
|  |  1/8 unav. |       |  +---------+  +---------+                  | |
|  |  Budget OK |       |  NetworkPolicy: ZONE ISOLATED               | |
|  |            |       +--------------------------------------------+ |
|  | Canary:    |       +--- YELLOW YELLOW -------------------------+  |
|  |  Sim: 3%   |       | tomato VITAMIN  Node:C      YELLOW WATCH |  |
|  |  Actual: ? |------>|  +---------+  +---------+                 |  |
|  |            | (amb) |  | Tom 85  |  | Spi 34  | <- pre-harv    |  |
|  | Admission: |       |  | YEL MON |  | BLK BLK |                 |  |
|  |  FR-CME-001|       |  +---------+  +---------+                 |  |
|  |  FR-CME-002|       |  PDB VIOLATED: 50% unavailable WARNING    |  |
|  |  ADMITTED  |       +-------------------------------------------+  |
|  |            |       +--- * GREEN ----------------------------+     |
|  |            |------>| herb SUPPORT  Node:D              * 94%|     |
|  +------------+       |  Stable. Basil VOCs protecting dome.   |     |
|                        +----------------------------------------+     |
|                                                                      |
| +- CANARY DEPLOYMENT (Virtual Lab) -------------------------------+  |
| | Strategy A -- Do Nothing        40% loss  X  (rejected)         |  |
| | Strategy B -- Standard          12% loss  ~  (suboptimal)       |  |
| | Strategy C -- Pre-emptive        3% loss  V  PROMOTED -> PROD   |  |
| |                                                                  |  |
| | Rollout: ########__ 80%   Confidence: 87% (Syngenta KB)        |  |
| +------------------------------------------------------------------+  |
|                                                                      |
| +- RESOURCE FLOW (DEGRADED) --------------------------------------+  |
| | * Solar -[1.26kW]-> z Grid --> drop Desal -[36L]-> plant Zones  |  |
| |   30% vvv           | 45%v      DEGRADED                        |  |
| |                      +-> shield Shields ACTIVE (priority)        |  |
| |                      +-> battery Battery 45% vv (draining)       |  |
| +------------------------------------------------------------------+  |
|                                                                      |
| +- EVENTS ----------------------------------------------------+      |
| | 0s   Warning  CMEImpact         cluster/eden   Radiation spike |    |
| | 1s   Normal   AdmissionCtrl     rule/FR-CME-001  ADMITTED      |    |
| | 2s   Normal   CanaryCreate      strategy/C       Simulating... |    |
| | 5s   Normal   CanaryPromote     strategy/C       3% -> PROD    |    |
| | 8s   Warning  NetworkPolicy     node/carb        ISOLATED      |    |
| | 10s  Warning  Triage            pod/wheat        RED: interv.  |    |
| | 12s  Warning  PDBViolation      node/vitamin     50% > budget  |    |
| | 15s  Normal   PreHarvest        pod/spinach      1.9kg secured |    |
| | 20s  Normal   StressHarden      pod/wheat        EC +0.4 mS/cm|    |
| +----------------------------------------------------------------+    |
|                                                                      |
| +- COUNCIL DEBATE ------------------------------------------------+  |
| | SENTINEL: CME impact. Radiation 263 uSv/hr. Shields active.     |  |
| | AQUA: Pre-stockpiled 580L. Autonomy: 7.2 sols. We're good.     |  |
| | FLORA: Wheat holding -- stress-hardened EC working. We wait.    |  |
| | COUNCIL VOTE: Strategy C -- unanimous (5/5).                    |  |
| +------------------------------------------------------------------+  |
+----------------------------------------------------------------------+
```

---

## Recovery — The Learning Event

After storm, the events that prove "learn and adapt":

```
| 0s   Normal   PostEventDebrief  dreamer/oracle   Predicted: 3% Actual: 2.7%  |
| 5s   Normal   FlightRuleCreate  rule/FR-CME-012  IF cme>1000 + BBCH 55-70... |
| 10s  Normal   FlightRuleCreate  rule/FR-CME-013  Stockpile at T-55h not T-48 |
| 15s  Normal   Reconciled        cluster/eden     Rules: 87 -> 89. Synced     |
```

---

## Pod Deep Dive — Click a Pod

When you click on a Pod (e.g., Soybean), it expands into a detailed view:

```
+---------------------------------------------------------------------+
| <- Back to Cluster    Pod: Soybean  Node:PROTEIN  Zone A            |
+---------------------------------------------------------------------+
|                                                                     |
|  +- PLANT VISUALIZATION -----------------------------------------+  |
|  |                                                               |  |
|  |         (large PlantSVG -- the dome cross-section)            |  |
|  |                                                               |  |
|  |              +--- glass dome arc ---+                         |  |
|  |             |    plant plant plant   |                        |  |
|  |             |    |||   |||   |||     |                        |  |
|  |             |   /||\  /||\  /||\    |                        |  |
|  |             |  / || \/ || \/ || \   |  health: 91%            |  |
|  |             |  | || || || || || |   |  BBCH 65: Full flower  |  |
|  |              \ | || || || || || | /                           |  |
|  |               +=====================+                        |  |
|  |               ~~~ Mars soil ~~~~~                             |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +- ConfigMap -----------+  +- Probes -------------------------+    |
|  | pH: 6.2               |  | Liveness:  * passing (30s ago)  |    |
|  | EC: 1.8 mS/cm         |  | Readiness: o not ready (30d)   |    |
|  | Temp: 22.3C            |  | Harvest:   Sol 277              |    |
|  | Humidity: 63%          |  | Started:   Sol 187              |    |
|  | VPD: 0.95 kPa         |  | Restarts:  0                   |    |
|  | DLI: 17.2 mol/m2/d    |  |                                 |    |
|  | Light: 82%             |  | Sidecar: Lentil (companion)    |    |
|  | CO2: 890 ppm           |  |  N-fixation -18% nutrient      |    |
|  +-----------------------+  +---------------------------------+    |
|                                                                     |
|  +- ResourceQuota -----------------------------------------------+  |
|  | Water:     1.75 / 3.0 L/sol   ########____  58%              |  |
|  | Light:     82 / 100%          ##########__  82%               |  |
|  | Nutrients: EC 1.8 / 3.0       ######______  60%               |  |
|  | Space:     20 / 30 m2         ########____  67%               |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +- Nutritional Output ------------------------------------------+  |
|  | Protein: 36.5g/100g -> 31.5% of crew protein need             |  |
|  | Calories: 446 kcal/100g -> 14.5% of crew calorie need         |  |
|  | Iron: 15.7mg/100g -> 29.0% of crew iron need                  |  |
|  | Fat: 19.9g/100g -> 7.3% of crew fat need                      |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +- Events ------------------------------------------------------+  |
|  | 30s  Normal  LivenessProbe  Sensors nominal                    |  |
|  | 1h   Normal  BBCH Advance   64 -> 65 (full flowering)          |  |
|  | 3d   Normal  Watering       2.1L delivered                     |  |
|  | 5d   Normal  Scheduled      Adjacent to Lentil (sidecar)       |  |
|  +---------------------------------------------------------------+  |
+---------------------------------------------------------------------+
```

---

## Node Deep Dive — Click a Node

Click a Node -> the dome section for that zone:

```
+---------------------------------------------------------------------+
| <- Back to Cluster    Node: PROTEIN  Zone A  30m2                   |
+---------------------------------------------------------------------+
|                                                                     |
|  +- DOME SECTION ------------------------------------------------+  |
|  |          +-------------------------------+                     |  |
|  |         /                                 \                    |  |
|  |        |   plant plant plant  plant plant   |                  |  |
|  |        |   |||||  |||||  |||  |||||  |||||  |                  |  |
|  |        |   Soybean Soybean    Lentil Lentil |                  |  |
|  |         \                                 /                    |  |
|  |          +===============================+                     |  |
|  |          ~~~ Mars soil ~~~~~~~~~~~~~~~                         |  |
|  +---------------------------------------------------------------+  |
|                                                                     |
|  +--- Pods --------------------------------------------------+      |
|  | +-----------------+  +-----------------+                   |      |
|  | | Soybean         |  | Lentil          |   <-> companion   |      |
|  | | 91% * BBCH 65   |  | 88% * BBCH 71  |                   |      |
|  | | Full flowering  |  | Fruit dev.      |                   |      |
|  | | Harvest: 30 sols|  | Harvest: 25 sols|                   |      |
|  | +-----------------+  +-----------------+                   |      |
|  +------------------------------------------------------------+      |
|                                                                     |
|  Sensors / ResourceQuota / Events (same detail level)               |
+---------------------------------------------------------------------+
```

---

## Resource Flow — The Hubble Layer

Not just a strip — a proper service dependency graph:

```
+- RESOURCE FLOW ---------------------------------------------------+
|                                                                   |
|   +--------+     +--------+     +--------+     +-------------+   |
|   |* SOLAR |---->|z POWER |---->|drop DESAL|-->|plant IRRIGATE|  |
|   | 4.2 kW |     | Grid   |     | 120L/s |     | 4 zones     |   |
|   | 100%   |     | 78%    |     |        |     +------+------+   |
|   +--------+     +---+----+     +--------+            |          |
|                      |                                |          |
|                 +----+----+                    +------+------+   |
|                 | LIGHTS  |                    | HARVEST     |   |
|                 | HEAT    |                    | kcal + vit  |   |
|                 | SHIELD  |                    +------+------+   |
|                 | BATTERY |                           |          |
|                 | 78%     |                    +------+------+   |
|                 +---------+                    | CREW        |   |
|                                                | 4 astronauts|   |
|   +----------------------+                     | VitC: 133%  |   |
|   | INGRESS              |                     | Iron: 112%  |   |
|   | Syngenta KB / DONKI  |                     | O2: 14.2%   |   |
|   | InSight / NASA POWER |                     +-------------+   |
|   +----------------------+                                       |
+-------------------------------------------------------------------+
```

Each box has a status dot. Arrows have animated flow indicators (dashed line animation).
During crisis, degraded links turn red, flow rates drop visibly.

---

## The "kubectl events" Stream

Live terminal-style event stream. This is *the* thing for AWS judges:

```
+- EVENTS ---------------------------------------------------------+
| AGE  TYPE     REASON           OBJECT             MESSAGE         |
| -----------------------------------------------------------------|
| 10s  Normal   LivenessProbe    pod/soybean        Sensors nominal|
| 30s  Normal   Reconciled       cluster/eden       Synced          |
| 1m   Normal   CronJob          dreamer/nightly    4,217 sims     |
| 2m   Warning  VPDDrift         node/vitamin       0.88 < target  |
| 5m   Normal   AdmissionCtrl    rule/FR-H-003      Armed: VPD fix |
| 8m   Normal   RollingUpdate    node/vitamin       Spinach cycle 5|
|                                                                   |
| During crisis, events flood in:                                   |
| 0s   Warning  CMEDetected      cluster/eden       1,247 km/s     |
| 1s   Normal   AdmissionCtrl    rule/FR-CME-001    ADMITTED        |
| 2s   Normal   CanaryCreate     strategy/C         Simulating...  |
| 5s   Normal   CanaryPromote    strategy/C         3% loss -> PROD|
| 8s   Warning  NetworkPolicy    node/carb          ISOLATED        |
| 10s  Warning  Triage           pod/wheat          RED: intervening|
| 12s  Warning  PDBViolation     node/vitamin       50% > budget   |
| 15s  Normal   PreHarvest       pod/spinach        1.9kg secured  |
| 20s  Normal   StressHarden     pod/wheat          EC +0.4 mS/cm  |
+-------------------------------------------------------------------+
```

---

## Mars Aesthetic

NOT dark space theme. Modern minimal with Mars CHARACTER:

- Light mode: clean white (#f5f5f7) background
- Mars terrain gradient at page bottom: subtle blend from transparent -> rgba(180, 83, 40, 0.06)
- Mars terrain silhouette: subtle SVG at very bottom -- stylized jagged mountains. Opacity 0.04 light, 0.08 dark.
- Subtle CSS-only particles: 10-15 dust motes, very slow, very low opacity
- State color shifts on terrain gradient:
  - Nominal: warm amber/brown (Mars default)
  - Alert: amber intensifies
  - Crisis: shifts to red
  - Recovery: shifts to cool blue
- Dark mode: Mars terrain at opacity ~0.1, background dark charcoal, dome glass with subtle luminous edge
- Font: Space Grotesk (labels) + JetBrains Mono (K8s vocabulary, data, events)
- Color palette: amber #e8913a accent, green #34d399 healthy, red #ef4444 critical, cyan #06b6d4 water

---

## State-Driven Transitions

All CSS transitions, 0.5s ease-out. No JS animation libraries.

### Nominal -> Alert
1. Alert banner slides in from top (CME countdown starts ticking)
2. Agent stream switches to SENTINEL warning
3. Node borders start getting amber glow
4. Resource flow values start changing (water climbing)
5. Mars terrain gradient shifts warmer
6. Cluster status: "Synced" -> "Warning: CME incoming"

### Alert -> Crisis (THE demo climax)
1. Node borders shift to triage colors (RED/YELLOW/GREEN/BLACK)
2. Cluster status: "Warning" -> "DEGRADED"
3. Connecting lines pulse red
4. Plant stress animations activate inside pod boxes
5. Canary Deployment panel auto-surfaces below tree (strategies)
6. Council Debate panel auto-surfaces
7. Events stream floods with crisis entries
8. Resource flow shows degraded links (red arrows, reduced throughput)
9. Mars terrain gradient shifts red
10. PDB status updates in cluster box

### Crisis -> Recovery
1. Background shifts from red -> blue
2. Node borders start returning to green
3. Plant stress animations ease
4. Events show PostEventDebrief, FlightRuleCreate
5. Agent stream shows ORACLE post-storm learning
6. Cluster status: "DEGRADED" -> "Recovering"

### Recovery -> Nominal
1. Full reversal. All green. "Synced" restored.
2. Flight rules count incremented (87 -> 89) -- subtle proof of learning
3. Crisis panels fade out
4. Mars terrain returns to nominal amber

---

## Interactions

### Zone Hover (on Node box)
- Node scales up slightly (transform: scale(1.02))
- Background brightens
- Show zone summary tooltip: sensors, resource quota, crop list
- Other nodes dim slightly (opacity: 0.7)
- CSS only -- no React state on hover

### Pod Hover (on Pod card inside Node)
- Pod card elevates (box-shadow increases)
- Show quick tooltip: plant type, health, BBCH, harvest countdown
- CSS only

### Node Click -> Zone Deep Dive
- Smooth transition: tree fades, zone dome section expands to fill center
- Shows: large PlantSVGs in dome cross-section, full sensor grid, companion info
- "<- Back to Cluster" button returns to tree view

### Pod Click -> Crop Deep Dive
- Smooth transition: tree fades, pod detail view fills center
- Shows: huge PlantSVG, ConfigMap, Probes, ResourceQuota, Nutritional Output, Events
- "<- Back to Cluster" or "<- Back to Node" navigation

### Dome Minimize Toggle (header button)
- Toggle between tree view (default) and compact mode
- Compact: tree shrinks to a single-line status bar, all detail panels expand below
- For post-demo exploration when judges want to see all data

---

## Why This Wins (Judge Lens)

### Visual Design (25%)
No other team has a spatial architecture visualization. The K8s tree with growing plants
inside pod boxes is memorable and unique. The crisis transformation is cinematic.

### Creativity (25%)
"ArgoCD for agriculture" is a category of one. The K8s mapping is not a claim in a doc --
it's the actual UI paradigm. AWS judges DISCOVER it. Syngenta judges see plants.

### Functionality (25%)
All data visible at a glance in the tree. No hidden panels needed. Events stream proves
real AI decisions. Reconciliation status proves autonomous operation.

### Pitch (25%)
The tree IS the pitch. "Each zone is a Node. Each crop is a Pod. Companion plants are
Sidecars. The Flight Rules Engine is an Admission Controller. And when a crisis hits,
you see NetworkPolicies enforce zone isolation, PodDisruptionBudgets protect critical
crops, and Canary Deployments test strategies before promoting to production."

AWS judge's jaw hits the floor.

---

## Build Priority

| Priority | Component | Why |
|----------|-----------|-----|
| **P0** | Cluster Tree layout (EDEN -> Nodes -> Pods with PlantSVGs) | THE hero visual |
| **P0** | Pod boxes with mini growing plants | The emotional hook |
| **P0** | Crisis transformation (borders, status, triage colors) | The demo climax |
| **P1** | Resource Flow strip (Hubble-style) | Completes the K8s story |
| **P1** | Events stream (kubectl format) | Proves real AI to AWS judges |
| **P1** | Node/Pod click deep-dive (dome view) | Interactive depth |
| **P2** | Canary Deployment card (Virtual Lab as K8s concept) | Clever mapping |
| **P2** | Reconciliation diff (desired vs actual) | Hidden depth |
| **P2** | Mars background aesthetic | Atmosphere |
| **P3** | Animated flow lines, sidecar visuals, PDB display | Polish |

---

## Implementation Plan

### New Components
1. `ClusterView.jsx` -- Main K8s resource tree with connected boxes
2. `ClusterBox.jsx` -- The EDEN cluster root node (left side)
3. `NodeBox.jsx` -- Zone node with mini plants + status indicators
4. `PodCard.jsx` -- Crop pod with PlantSVG + health + BBCH (rename from existing)
5. `ResourceFlow.jsx` -- Hubble-style animated resource chain
6. `EventStream.jsx` -- kubectl events format stream
7. `CanaryDeployment.jsx` -- Virtual Lab as K8s canary concept
8. `ZoneDeepDive.jsx` -- Node click -> dome section view
9. `PodDeepDive.jsx` -- Pod click -> full crop detail view
10. `ConnectorLine.jsx` -- SVG connector lines between tree nodes

### Preserved Components
- PlantSVG (used inside PodCards and deep-dive views)
- MicroBar (utility)
- AlertBanner (enhanced with K8s status)
- Panel (utility)
- NutritionPanel, FlightRules, AgentLog, MemoryWall (expandable sections)
- MissionTimeline
- VirtualLab -> becomes CanaryDeployment
- TriagePanel (shown during crisis, uses PDB vocabulary)
- useDemo hook (state machine)
- Mock data layer (all reused, extended with K8s fields)

### Current Dashboard
Preserved as-is. Accessible as secondary view. Not deleted.

### Technical Notes
- All transitions: CSS transitions + transforms. No animation libraries.
- Tree layout: CSS Grid (cluster column + node column). Not a canvas.
- Connector lines: SVG positioned absolutely between boxes.
- PlantSVGs inside pods: rendered at ~60x80px scale. Grow based on BBCH.
- Events stream: auto-scrolling div with monospace font, kubectl-style formatting.
- Resource flow: CSS Grid or Flexbox with SVG arrow connectors.
- State drives everything: useDemo hook state -> CSS classes on root -> all visual changes cascade.

---

## Concept A: "The Dome" (preserved as deep-dive)

The dome visualization from the earlier design session is NOT abandoned.
It becomes the Node deep-dive experience -- when you click a Node in the tree,
you enter the dome section for that zone. Large PlantSVGs, glass arc, Mars soil.
This gives the immersive "walk into the greenhouse" experience within the K8s architecture.
