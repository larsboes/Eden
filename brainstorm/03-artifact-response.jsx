import { useState, useEffect, useRef, useCallback } from "react";

// ─── DATA & CONSTANTS ────────────────────────────────────────────────────────
const ZONES = [
  { id:"A", name:"TUBERS", crops:["Potato","Sweet Potato"], icon:"🥔", temp:22.3, humidity:64, health:94, water:3.1, light:82, co2:890, ph:6.2, growthRate:1.02, pods:24, activePods:23, status:"nominal" },
  { id:"B", name:"GREENS", crops:["Spinach","Kale","Lettuce"], icon:"🥬", temp:19.8, humidity:71, health:87, water:2.4, light:76, co2:920, ph:6.5, growthRate:0.97, pods:32, activePods:30, status:"warning" },
  { id:"C", name:"LEGUMES", crops:["Soybean","Lentil","Pea"], icon:"🫘", temp:23.7, humidity:59, health:91, water:1.9, light:80, co2:870, ph:6.8, growthRate:1.05, pods:20, activePods:20, status:"nominal" },
  { id:"D", name:"FRUITS", crops:["Tomato","Strawberry"], icon:"🍅", temp:24.1, humidity:67, health:72, water:3.8, light:88, co2:850, ph:6.0, growthRate:0.84, pods:18, activePods:15, status:"critical" },
];

const CREW = [
  { name:"Cmdr. Chen", role:"Commander", kcal:2100, kcalActual:1980, protein:92, iron:78, calcium:88, vitC:95, vitD:82, fiber:91, img:"👩‍🚀" },
  { name:"Dr. Okonkwo", role:"Science Lead", kcal:1900, kcalActual:1870, protein:96, iron:94, calcium:91, vitC:89, vitD:78, fiber:87, img:"👨‍🔬" },
  { name:"Eng. Volkov", role:"Engineer", kcal:2300, kcalActual:2150, protein:88, iron:85, calcium:71, vitC:82, vitD:90, fiber:79, img:"👨‍🚀" },
  { name:"Spc. Reyes", role:"Botanist", kcal:2000, kcalActual:1940, protein:90, iron:91, calcium:86, vitC:68, vitD:85, fiber:94, img:"👩‍🔬" },
];

const FLIGHT_RULES = [
  { id:"FR-012", rule:"Solar < 40% → Zone isolation", status:"armed", triggered:0 },
  { id:"FR-034", rule:"Humidity > 85% → Vent cycle", status:"triggered", triggered:2 },
  { id:"FR-067", rule:"pH drift > 0.5 → Nutrient flush", status:"armed", triggered:0 },
  { id:"FR-089", rule:"Temp > 30°C → Emergency cool", status:"armed", triggered:0 },
  { id:"FR-102", rule:"Water < 500L → Ration protocol", status:"armed", triggered:0 },
  { id:"FR-118", rule:"Crop health < 60% → Triage eval", status:"monitoring", triggered:1 },
  { id:"FR-145", rule:"Dust opacity > 0.7 → Solar backup", status:"armed", triggered:0 },
  { id:"FR-201", rule:"Pathogen detect → Quarantine zone", status:"armed", triggered:0 },
];

const AGENT_LOG = [
  { time:"14:31:42", agent:"NUTRITIONIST", msg:"Crew vitamin C trending ↓ — recommending strawberry harvest acceleration", type:"advisory" },
  { time:"14:29:18", agent:"RESOURCE-MGR", msg:"Water recycler efficiency at 94.2% — nominal. Next maintenance: Sol 224", type:"info" },
  { time:"14:27:03", agent:"CROP-ADVOCATE-D", msg:"Zone D tomato cluster 3 showing early blossom-end rot. Requesting calcium boost", type:"warning" },
  { time:"14:24:55", agent:"TRIAGE-ENGINE", msg:"Salvageability score Zone D: 0.68. Recommend partial water realloc from Zone D→A", type:"decision" },
  { time:"14:22:30", agent:"DREAM-ENGINE", msg:"Overnight batch complete: 4,217 scenarios. 3 new flight rules proposed", type:"info" },
  { time:"14:19:11", agent:"FLIGHT-CTRL", msg:"FR-034 triggered: Zone B humidity spike 86%. Vent cycle initiated", type:"alert" },
  { time:"14:15:44", agent:"RESOURCE-MGR", msg:"Solar array output dropping — dust accumulation detected. Current: 73%", type:"warning" },
  { time:"14:12:08", agent:"EXPLORER", msg:"Geo-scan complete: Ice deposit confirmed 2.3km NNW. Yield est: 340L extractable", type:"info" },
];

const HARVEST_SCHEDULE = [
  { crop:"Lettuce", zone:"B", sol:219, kg:2.8, status:"ready" },
  { crop:"Spinach", zone:"B", sol:223, kg:1.9, status:"growing" },
  { crop:"Strawberry", zone:"D", sol:228, kg:0.6, status:"growing" },
  { crop:"Pea", zone:"C", sol:235, kg:3.2, status:"growing" },
  { crop:"Potato", zone:"A", sol:251, kg:8.4, status:"growing" },
  { crop:"Tomato", zone:"D", sol:260, kg:2.1, status:"at-risk" },
  { crop:"Soybean", zone:"C", sol:272, kg:4.7, status:"growing" },
  { crop:"Kale", zone:"B", sol:240, kg:1.4, status:"growing" },
];

const TRIAGE_DATA = [
  { zone:"A", score:0.94, trend:"stable", action:"Maintain current allocation" },
  { zone:"B", score:0.82, trend:"improving", action:"Monitor humidity post-vent" },
  { zone:"C", score:0.89, trend:"stable", action:"No intervention needed" },
  { zone:"D", score:0.68, trend:"declining", action:"Partial water realloc → Zone A" },
];

// ─── UTILITY COMPONENTS ──────────────────────────────────────────────────────

const StatusDot = ({ status }) => {
  const colors = { nominal:"#10b981", warning:"#f59e0b", critical:"#ef4444", monitoring:"#6366f1" };
  return <span style={{ display:"inline-block", width:8, height:8, borderRadius:"50%", background:colors[status]||"#6b7280", boxShadow:`0 0 6px ${colors[status]||"#6b7280"}`, marginRight:6 }} />;
};

const MicroBar = ({ value, max=100, color="#00e5ff", height=4, warn=null, crit=null }) => {
  let barColor = color;
  if(crit && value < crit) barColor = "#ef4444";
  else if(warn && value < warn) barColor = "#f59e0b";
  return (
    <div style={{ width:"100%", height, background:"rgba(255,255,255,0.06)", borderRadius:2, overflow:"hidden" }}>
      <div style={{ width:`${Math.min((value/max)*100,100)}%`, height:"100%", background:barColor, borderRadius:2, transition:"width 1s ease" }} />
    </div>
  );
};

const GaugeRing = ({ value, max=100, size=54, stroke=4, color="#00e5ff", label }) => {
  const r = (size-stroke)/2;
  const circ = 2*Math.PI*r;
  const pct = Math.min(value/max,1);
  let c = color;
  if(value/max < 0.3) c="#ef4444"; else if(value/max < 0.6) c="#f59e0b";
  return (
    <div style={{ position:"relative", width:size, height:size, flexShrink:0 }}>
      <svg width={size} height={size} style={{ transform:"rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={c} strokeWidth={stroke} strokeDasharray={circ} strokeDashoffset={circ*(1-pct)} strokeLinecap="round" style={{ transition:"stroke-dashoffset 1s ease" }} />
      </svg>
      <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center" }}>
        <span style={{ fontSize:11, fontWeight:700, color:c, fontFamily:"'Share Tech Mono',monospace" }}>{value}</span>
        {label && <span style={{ fontSize:7, color:"#64748b", textTransform:"uppercase", letterSpacing:1 }}>{label}</span>}
      </div>
    </div>
  );
};

const Scanline = () => (
  <div style={{ position:"fixed", inset:0, pointerEvents:"none", zIndex:9999, background:"repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,229,255,0.008) 2px, rgba(0,229,255,0.008) 4px)" }} />
);

// ─── MAIN DASHBOARD ──────────────────────────────────────────────────────────

export default function EdenDashboard() {
  const [sol, setSol] = useState(217);
  const [time, setTime] = useState({ h:14, m:32, s:7 });
  const [zones, setZones] = useState(ZONES);
  const [alertPulse, setAlertPulse] = useState(true);
  const [selectedZone, setSelectedZone] = useState(null);
  const [dreamCount, setDreamCount] = useState(4217);
  const [survivalProb, setSurvivalProb] = useState(96.2);
  const [waterLevel, setWaterLevel] = useState(847);
  const [energyLevel, setEnergyLevel] = useState(73);
  const [activeFlightRules, setActiveFlightRules] = useState(247);

  // Simulated clock
  useEffect(() => {
    const iv = setInterval(() => {
      setTime(t => {
        let { h,m,s } = t;
        s++;
        if(s>=60){ s=0; m++; }
        if(m>=60){ m=0; h++; }
        if(h>=24){ h=0; }
        return { h,m,s };
      });
    }, 1000);
    return () => clearInterval(iv);
  }, []);

  // Simulated data fluctuation
  useEffect(() => {
    const iv = setInterval(() => {
      setZones(zz => zz.map(z => ({
        ...z,
        temp: +(z.temp + (Math.random()-0.5)*0.3).toFixed(1),
        humidity: Math.max(40,Math.min(95, z.humidity + Math.round((Math.random()-0.5)*2))),
        co2: Math.max(800,Math.min(1000, z.co2 + Math.round((Math.random()-0.5)*10))),
      })));
      setDreamCount(d => d + Math.floor(Math.random()*3));
      setWaterLevel(w => +(w - 0.01 + Math.random()*0.02).toFixed(1));
      setEnergyLevel(e => Math.max(60,Math.min(100, +(e + (Math.random()-0.5)*0.5).toFixed(1))));
    }, 2000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const iv = setInterval(() => setAlertPulse(p => !p), 1200);
    return () => clearInterval(iv);
  }, []);

  const pad = n => String(n).padStart(2,'0');
  const mtc = `${pad(time.h)}:${pad(time.m)}:${pad(time.s)} MTC`;

  const panelStyle = {
    background:"linear-gradient(135deg, rgba(15,23,42,0.95), rgba(10,14,23,0.98))",
    border:"1px solid rgba(0,229,255,0.12)",
    borderRadius:6,
    padding:"10px 12px",
    position:"relative",
    overflow:"hidden",
  };

  const panelHeaderStyle = {
    fontSize:9,
    fontWeight:700,
    letterSpacing:2.5,
    textTransform:"uppercase",
    color:"#00e5ff",
    marginBottom:8,
    fontFamily:"'Orbitron',sans-serif",
    display:"flex",
    alignItems:"center",
    gap:6,
  };

  const dataLabelStyle = { fontSize:9, color:"#64748b", textTransform:"uppercase", letterSpacing:1, fontFamily:"'Share Tech Mono',monospace" };
  const dataValueStyle = { fontSize:13, color:"#e2e8f0", fontWeight:600, fontFamily:"'Share Tech Mono',monospace" };
  const smallVal = { fontSize:11, color:"#cbd5e1", fontFamily:"'Share Tech Mono',monospace" };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Share+Tech+Mono&family=Exo+2:wght@300;400;500;600;700&display=swap');
        * { margin:0; padding:0; box-sizing:border-box; }
        ::-webkit-scrollbar { width:3px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:rgba(0,229,255,0.2); border-radius:3px; }
        @keyframes pulse-cyan { 0%,100%{box-shadow:0 0 4px rgba(0,229,255,0.2)} 50%{box-shadow:0 0 12px rgba(0,229,255,0.5)} }
        @keyframes pulse-red { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes scan { 0%{transform:translateY(-100%)} 100%{transform:translateY(100vh)} }
        @keyframes fadeSlideIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        .panel-glow:hover { border-color:rgba(0,229,255,0.3) !important; box-shadow:0 0 20px rgba(0,229,255,0.06) !important; }
        .zone-card:hover { border-color:rgba(0,229,255,0.4) !important; transform:scale(1.01); }
        .agent-row { animation:fadeSlideIn 0.4s ease both; }
      `}</style>
      <Scanline />
      <div style={{
        width:"100%", minHeight:"100vh", background:"#060a13",
        backgroundImage:"radial-gradient(ellipse at 20% 50%, rgba(0,229,255,0.03) 0%, transparent 50%), radial-gradient(ellipse at 80% 20%, rgba(99,102,241,0.03) 0%, transparent 50%)",
        fontFamily:"'Exo 2',sans-serif", color:"#e2e8f0", padding:10,
        display:"flex", flexDirection:"column", gap:8,
      }}>

        {/* ═══ HEADER BAR ═══ */}
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"8px 16px", background:"linear-gradient(90deg, rgba(0,229,255,0.06), transparent, rgba(0,229,255,0.06))", border:"1px solid rgba(0,229,255,0.15)", borderRadius:6 }}>
          <div style={{ display:"flex", alignItems:"center", gap:14 }}>
            <span style={{ fontFamily:"'Orbitron',sans-serif", fontSize:16, fontWeight:800, color:"#00e5ff", letterSpacing:3 }}>EDEN</span>
            <span style={{ fontSize:9, color:"#64748b", letterSpacing:2, fontFamily:"'Share Tech Mono',monospace", borderLeft:"1px solid rgba(255,255,255,0.1)", paddingLeft:12 }}>ENGINEERED DECISION-MAKING FOR EXTRATERRESTRIAL NURTURE</span>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:20 }}>
            <div style={{ textAlign:"center" }}>
              <div style={{ fontSize:8, color:"#64748b", letterSpacing:2, fontFamily:"'Share Tech Mono',monospace" }}>MISSION SOL</div>
              <div style={{ fontSize:20, fontWeight:800, fontFamily:"'Orbitron',sans-serif", color:"#f0f4ff", letterSpacing:2 }}>{sol}</div>
            </div>
            <div style={{ width:1, height:28, background:"rgba(255,255,255,0.1)" }} />
            <div style={{ textAlign:"center" }}>
              <div style={{ fontSize:8, color:"#64748b", letterSpacing:2, fontFamily:"'Share Tech Mono',monospace" }}>MARS TIME</div>
              <div style={{ fontSize:16, fontWeight:600, fontFamily:"'Share Tech Mono',monospace", color:"#00e5ff" }}>{mtc}</div>
            </div>
            <div style={{ width:1, height:28, background:"rgba(255,255,255,0.1)" }} />
            <div style={{ display:"flex", alignItems:"center", gap:6 }}>
              <StatusDot status="nominal" />
              <span style={{ fontSize:10, fontFamily:"'Share Tech Mono',monospace", color:"#10b981" }}>SYS NOMINAL</span>
            </div>
            <div style={{ display:"flex", alignItems:"center", gap:6, padding:"4px 10px", borderRadius:4, background: alertPulse ? "rgba(239,68,68,0.15)" : "rgba(239,68,68,0.05)", border:"1px solid rgba(239,68,68,0.3)", cursor:"pointer", transition:"all 0.3s" }}>
              <span style={{ fontSize:10, fontFamily:"'Orbitron',sans-serif", fontWeight:700, color:"#ef4444", animation:"pulse-red 1.2s infinite" }}>⚠ 3 ALERTS</span>
            </div>
          </div>
        </div>

        {/* ═══ MAIN GRID ═══ */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 2fr 1fr", gap:8, flex:1 }}>

          {/* ─── LEFT COLUMN ─── */}
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>

            {/* MARS ENVIRONMENT */}
            <div className="panel-glow" style={{ ...panelStyle, flex:"0 0 auto" }}>
              <div style={panelHeaderStyle}>
                <span style={{ fontSize:12 }}>🔴</span> MARS ENVIRONMENT
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
                {[
                  { label:"EXT TEMP", value:"-63°C", sub:"Surface" },
                  { label:"PRESSURE", value:"610 Pa", sub:"Atmos" },
                  { label:"SOLAR IRR", value:"590 W/m²", sub:"Current" },
                  { label:"WIND", value:"12 m/s", sub:"NNW" },
                  { label:"DUST TAU", value:"0.42", sub:"Opacity" },
                  { label:"UV INDEX", value:"HIGH", sub:"Shield active" },
                ].map((d,i) => (
                  <div key={i} style={{ padding:"6px 8px", background:"rgba(255,255,255,0.02)", borderRadius:4, border:"1px solid rgba(255,255,255,0.04)" }}>
                    <div style={dataLabelStyle}>{d.label}</div>
                    <div style={dataValueStyle}>{d.value}</div>
                    <div style={{ fontSize:8, color:"#475569" }}>{d.sub}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop:8, padding:"6px 8px", background:"rgba(245,158,11,0.08)", border:"1px solid rgba(245,158,11,0.2)", borderRadius:4 }}>
                <div style={{ fontSize:9, color:"#f59e0b", fontFamily:"'Share Tech Mono',monospace" }}>⚡ DUST STORM WARNING — Sol 219-222 | Prob: 67%</div>
              </div>
            </div>

            {/* RESOURCES */}
            <div className="panel-glow" style={{ ...panelStyle, flex:1 }}>
              <div style={panelHeaderStyle}>💧 RESOURCES & CIRCULAR ECONOMY</div>
              {[
                { name:"WATER RESERVE", val:waterLevel, max:1200, unit:"L", rate:"-12.3 L/day", recyc:"94.2% recycled", color:"#3b82f6" },
                { name:"ENERGY (SOLAR)", val:energyLevel, max:100, unit:"%", rate:"4.2 kWh avail", recyc:"Panels at 73%", color:"#f59e0b" },
                { name:"NITROGEN", val:78, max:100, unit:"%", rate:"Consumption normal", recyc:"Composting active", color:"#10b981" },
                { name:"PHOSPHORUS", val:65, max:100, unit:"%", rate:"-0.8%/sol", recyc:"From waste stream", color:"#8b5cf6" },
                { name:"POTASSIUM", val:82, max:100, unit:"%", rate:"Stable", recyc:"Ash recycling on", color:"#ec4899" },
              ].map((r,i) => (
                <div key={i} style={{ marginBottom:8 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:3 }}>
                    <span style={{ ...dataLabelStyle, fontSize:8 }}>{r.name}</span>
                    <span style={{ fontFamily:"'Share Tech Mono',monospace", fontSize:12, fontWeight:700, color:r.color }}>{typeof r.val === 'number' ? (r.val > 200 ? r.val.toFixed(0) : r.val.toFixed(1)) : r.val}{r.unit}</span>
                  </div>
                  <MicroBar value={r.val} max={r.max} color={r.color} height={5} warn={r.max*0.3} crit={r.max*0.15} />
                  <div style={{ display:"flex", justifyContent:"space-between", marginTop:2 }}>
                    <span style={{ fontSize:8, color:"#475569" }}>{r.rate}</span>
                    <span style={{ fontSize:8, color:"#475569" }}>♻ {r.recyc}</span>
                  </div>
                </div>
              ))}

              {/* Circular Flow Mini Diagram */}
              <div style={{ marginTop:4, padding:8, background:"rgba(0,229,255,0.03)", borderRadius:4, border:"1px dashed rgba(0,229,255,0.15)", textAlign:"center" }}>
                <div style={{ fontSize:8, color:"#00e5ff", fontFamily:"'Orbitron',sans-serif", letterSpacing:2, marginBottom:4 }}>CIRCULAR FLOW</div>
                <div style={{ fontSize:10, color:"#94a3b8", fontFamily:"'Share Tech Mono',monospace", lineHeight:1.6 }}>
                  Crops → Crew → Waste → Compost → Nutrients → Crops<br/>
                  H₂O → Irrigation → Transpiration → Condenser → H₂O<br/>
                  CO₂ → Plants → O₂ → Crew → CO₂
                </div>
              </div>
            </div>
          </div>

          {/* ─── CENTER COLUMN ─── */}
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>

            {/* ZONE GRID */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
              {zones.map(z => (
                <div key={z.id} className="zone-card panel-glow" onClick={() => setSelectedZone(selectedZone===z.id ? null : z.id)} style={{
                  ...panelStyle,
                  cursor:"pointer",
                  transition:"all 0.3s",
                  borderColor: z.status==="critical" ? "rgba(239,68,68,0.3)" : z.status==="warning" ? "rgba(245,158,11,0.2)" : "rgba(0,229,255,0.12)",
                  ...(selectedZone===z.id ? { borderColor:"rgba(0,229,255,0.5)", boxShadow:"0 0 20px rgba(0,229,255,0.1)" } : {}),
                }}>
                  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
                    <div style={panelHeaderStyle}>
                      <span style={{ fontSize:14 }}>{z.icon}</span>
                      ZONE {z.id} — {z.name}
                    </div>
                    <StatusDot status={z.status} />
                  </div>

                  {/* Health Ring + Vitals */}
                  <div style={{ display:"flex", gap:10, alignItems:"center", marginBottom:8 }}>
                    <GaugeRing value={z.health} size={58} color={z.health>85?"#10b981":z.health>70?"#f59e0b":"#ef4444"} label="HEALTH" />
                    <div style={{ flex:1, display:"grid", gridTemplateColumns:"1fr 1fr", gap:4 }}>
                      {[
                        { l:"TEMP", v:`${z.temp}°C` },
                        { l:"HUMID", v:`${z.humidity}%` },
                        { l:"CO₂", v:`${z.co2}ppm` },
                        { l:"pH", v:z.ph },
                        { l:"LIGHT", v:`${z.light}%` },
                        { l:"H₂O", v:`${z.water}L/d` },
                      ].map((d,i) => (
                        <div key={i}>
                          <div style={{ fontSize:7, color:"#475569", letterSpacing:1 }}>{d.l}</div>
                          <div style={{ fontSize:10, color:"#cbd5e1", fontFamily:"'Share Tech Mono',monospace", fontWeight:600 }}>{d.v}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Pod Status Strip */}
                  <div style={{ display:"flex", gap:2, flexWrap:"wrap" }}>
                    {Array.from({ length:z.pods }).map((_,i) => (
                      <div key={i} style={{
                        width:8, height:8, borderRadius:2,
                        background: i < z.activePods ? (z.health > 85 ? "#10b981" : z.health > 70 ? "#f59e0b" : "#ef4444") : "rgba(255,255,255,0.06)",
                        opacity: i < z.activePods ? 0.8 : 0.3,
                      }} />
                    ))}
                  </div>
                  <div style={{ fontSize:8, color:"#64748b", marginTop:4, fontFamily:"'Share Tech Mono',monospace" }}>
                    {z.activePods}/{z.pods} pods active · Growth: {z.growthRate}x · Crops: {z.crops.join(", ")}
                  </div>
                </div>
              ))}
            </div>

            {/* CREW NUTRITION */}
            <div className="panel-glow" style={panelStyle}>
              <div style={panelHeaderStyle}>👨‍🚀 CREW NUTRITION — 4 ASTRONAUTS</div>
              <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8 }}>
                {CREW.map((c,i) => (
                  <div key={i} style={{ padding:8, background:"rgba(255,255,255,0.02)", borderRadius:4, border:"1px solid rgba(255,255,255,0.05)" }}>
                    <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:6 }}>
                      <span style={{ fontSize:18 }}>{c.img}</span>
                      <div>
                        <div style={{ fontSize:10, fontWeight:700, color:"#e2e8f0" }}>{c.name}</div>
                        <div style={{ fontSize:8, color:"#64748b" }}>{c.role}</div>
                      </div>
                    </div>
                    <div style={{ marginBottom:4 }}>
                      <div style={{ display:"flex", justifyContent:"space-between" }}>
                        <span style={{ fontSize:8, color:"#64748b" }}>KCAL</span>
                        <span style={{ fontSize:9, fontFamily:"'Share Tech Mono',monospace", color: c.kcalActual/c.kcal > 0.9 ? "#10b981" : "#f59e0b" }}>{c.kcalActual}/{c.kcal}</span>
                      </div>
                      <MicroBar value={c.kcalActual} max={c.kcal} color="#3b82f6" height={3} />
                    </div>
                    {[
                      { l:"Protein", v:c.protein },
                      { l:"Iron", v:c.iron },
                      { l:"Calcium", v:c.calcium },
                      { l:"Vit C", v:c.vitC },
                      { l:"Vit D", v:c.vitD },
                      { l:"Fiber", v:c.fiber },
                    ].map((n,j) => (
                      <div key={j} style={{ marginBottom:2 }}>
                        <div style={{ display:"flex", justifyContent:"space-between" }}>
                          <span style={{ fontSize:7, color:"#475569" }}>{n.l}</span>
                          <span style={{ fontSize:8, fontFamily:"'Share Tech Mono',monospace", color: n.v > 85 ? "#94a3b8" : n.v > 70 ? "#f59e0b" : "#ef4444" }}>{n.v}%</span>
                        </div>
                        <MicroBar value={n.v} color={n.v>85?"#10b981":n.v>70?"#f59e0b":"#ef4444"} height={2} warn={75} crit={60} />
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* HARVEST FORECAST */}
            <div className="panel-glow" style={panelStyle}>
              <div style={panelHeaderStyle}>📅 HARVEST FORECAST</div>
              <div style={{ display:"flex", gap:4, flexWrap:"wrap" }}>
                {HARVEST_SCHEDULE.sort((a,b)=>a.sol-b.sol).map((h,i) => {
                  const urgency = h.sol - sol;
                  const bg = h.status==="ready" ? "rgba(16,185,129,0.15)" : h.status==="at-risk" ? "rgba(239,68,68,0.1)" : "rgba(255,255,255,0.02)";
                  const border = h.status==="ready" ? "rgba(16,185,129,0.3)" : h.status==="at-risk" ? "rgba(239,68,68,0.2)" : "rgba(255,255,255,0.06)";
                  return (
                    <div key={i} style={{ padding:"5px 8px", background:bg, border:`1px solid ${border}`, borderRadius:4, minWidth:90 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline" }}>
                        <span style={{ fontSize:10, fontWeight:600, color:"#e2e8f0" }}>{h.crop}</span>
                        <span style={{ fontSize:8, color:"#64748b" }}>Z-{h.zone}</span>
                      </div>
                      <div style={{ fontSize:9, fontFamily:"'Share Tech Mono',monospace", color: h.status==="ready" ? "#10b981" : h.status==="at-risk" ? "#ef4444" : "#94a3b8" }}>
                        Sol {h.sol} · {h.kg}kg {h.status==="ready" && "✓ READY"}
                      </div>
                      <MicroBar value={Math.max(0, 1-urgency/80)*100} color={h.status==="ready"?"#10b981":h.status==="at-risk"?"#ef4444":"#3b82f6"} height={2} />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* ─── RIGHT COLUMN ─── */}
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>

            {/* DREAM ENGINE */}
            <div className="panel-glow" style={{ ...panelStyle, borderColor:"rgba(139,92,246,0.2)" }}>
              <div style={{ ...panelHeaderStyle, color:"#a78bfa" }}>🌙 DREAM ENGINE</div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:8 }}>
                <div style={{ textAlign:"center", padding:6, background:"rgba(139,92,246,0.06)", borderRadius:4 }}>
                  <div style={{ fontSize:20, fontWeight:800, fontFamily:"'Orbitron',sans-serif", color:"#a78bfa" }}>{dreamCount.toLocaleString()}</div>
                  <div style={{ fontSize:8, color:"#64748b", letterSpacing:1 }}>SCENARIOS SIMULATED</div>
                </div>
                <div style={{ textAlign:"center", padding:6, background:"rgba(16,185,129,0.06)", borderRadius:4 }}>
                  <div style={{ fontSize:20, fontWeight:800, fontFamily:"'Orbitron',sans-serif", color:"#10b981" }}>{survivalProb}%</div>
                  <div style={{ fontSize:8, color:"#64748b", letterSpacing:1 }}>SURVIVAL PROBABILITY</div>
                </div>
              </div>
              <div style={{ fontSize:9, color:"#94a3b8", marginBottom:4, fontFamily:"'Share Tech Mono',monospace" }}>WORST CASE: Cascading power failure Sol 340</div>
              <div style={{ fontSize:9, color:"#94a3b8", marginBottom:4, fontFamily:"'Share Tech Mono',monospace" }}>BEST CASE: +18% yield with optimized light schedule</div>
              <div style={{ fontSize:9, color:"#a78bfa", fontFamily:"'Share Tech Mono',monospace" }}>NEW FLIGHT RULES PROPOSED: 3</div>
              <div style={{ marginTop:8, padding:6, background:"rgba(139,92,246,0.05)", border:"1px solid rgba(139,92,246,0.15)", borderRadius:4 }}>
                <div style={{ fontSize:8, color:"#7c3aed", fontFamily:"'Orbitron',sans-serif", letterSpacing:1.5, marginBottom:3 }}>NEXT DREAM CYCLE</div>
                <div style={{ fontSize:9, color:"#94a3b8", fontFamily:"'Share Tech Mono',monospace" }}>Focus: Dust storm recovery · Zone D triage paths · Water ration variants</div>
              </div>
            </div>

            {/* AGENT CONSORTIUM */}
            <div className="panel-glow" style={{ ...panelStyle, flex:1, display:"flex", flexDirection:"column" }}>
              <div style={panelHeaderStyle}>🤖 AGENT CONSORTIUM</div>
              <div style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column", gap:4 }}>
                {AGENT_LOG.map((a,i) => {
                  const agentColor = {
                    "NUTRITIONIST":"#ec4899", "RESOURCE-MGR":"#3b82f6", "CROP-ADVOCATE-D":"#f59e0b",
                    "TRIAGE-ENGINE":"#ef4444", "DREAM-ENGINE":"#a78bfa", "FLIGHT-CTRL":"#10b981", "EXPLORER":"#06b6d4"
                  }[a.agent] || "#64748b";
                  return (
                    <div key={i} className="agent-row" style={{ padding:"6px 8px", background:"rgba(255,255,255,0.015)", borderRadius:4, borderLeft:`2px solid ${agentColor}`, animationDelay:`${i*0.05}s` }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:2 }}>
                        <span style={{ fontSize:8, fontWeight:700, color:agentColor, fontFamily:"'Orbitron',sans-serif", letterSpacing:1 }}>{a.agent}</span>
                        <span style={{ fontSize:8, color:"#475569", fontFamily:"'Share Tech Mono',monospace" }}>{a.time}</span>
                      </div>
                      <div style={{ fontSize:9, color:"#94a3b8", lineHeight:1.4 }}>{a.msg}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* TRIAGE + FLIGHT RULES */}
            <div className="panel-glow" style={panelStyle}>
              <div style={panelHeaderStyle}>⚖️ ETHICAL TRIAGE</div>
              <div style={{ display:"flex", flexDirection:"column", gap:4, marginBottom:8 }}>
                {TRIAGE_DATA.map((t,i) => (
                  <div key={i} style={{ display:"flex", alignItems:"center", gap:8, padding:"4px 6px", background:"rgba(255,255,255,0.02)", borderRadius:3 }}>
                    <span style={{ fontSize:10, fontWeight:700, fontFamily:"'Orbitron',sans-serif", color:"#00e5ff", width:32 }}>Z-{t.zone}</span>
                    <div style={{ flex:1 }}>
                      <MicroBar value={t.score*100} color={t.score>0.85?"#10b981":t.score>0.7?"#f59e0b":"#ef4444"} height={6} warn={70} crit={50} />
                    </div>
                    <span style={{ fontSize:11, fontWeight:700, fontFamily:"'Share Tech Mono',monospace", color:t.score>0.85?"#10b981":t.score>0.7?"#f59e0b":"#ef4444", width:36, textAlign:"right" }}>{(t.score*100).toFixed(0)}%</span>
                    <span style={{ fontSize:8, color: t.trend==="declining"?"#ef4444":t.trend==="improving"?"#10b981":"#64748b" }}>{t.trend==="declining"?"▼":t.trend==="improving"?"▲":"─"}</span>
                  </div>
                ))}
              </div>
              <div style={{ padding:"6px 8px", background:"rgba(239,68,68,0.06)", border:"1px solid rgba(239,68,68,0.15)", borderRadius:4 }}>
                <div style={{ fontSize:9, color:"#ef4444", fontFamily:"'Share Tech Mono',monospace", lineHeight:1.5 }}>
                  ⚠ TRIAGE ADVISORY: "I chose to deprioritize Zone D spinach. Crew iron intake drops 12% below optimal by Sol 240. Mitigation: lentil allocation from dry stores. Confidence: 91%"
                </div>
              </div>
            </div>

            {/* FLIGHT RULES */}
            <div className="panel-glow" style={panelStyle}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div style={panelHeaderStyle}>📋 FLIGHT RULES ENGINE</div>
                <span style={{ fontSize:12, fontWeight:800, fontFamily:"'Orbitron',sans-serif", color:"#00e5ff" }}>{activeFlightRules} ACTIVE</span>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:3, maxHeight:120, overflowY:"auto" }}>
                {FLIGHT_RULES.map((fr,i) => (
                  <div key={i} style={{ display:"flex", alignItems:"center", gap:6, padding:"3px 6px", background: fr.status==="triggered" ? "rgba(245,158,11,0.08)" : "rgba(255,255,255,0.015)", borderRadius:3, borderLeft: fr.status==="triggered" ? "2px solid #f59e0b" : fr.status==="monitoring" ? "2px solid #6366f1" : "2px solid rgba(255,255,255,0.06)" }}>
                    <span style={{ fontSize:8, fontWeight:700, fontFamily:"'Share Tech Mono',monospace", color:"#64748b", width:40 }}>{fr.id}</span>
                    <span style={{ fontSize:9, color:"#94a3b8", flex:1 }}>{fr.rule}</span>
                    <span style={{ fontSize:7, padding:"1px 5px", borderRadius:3, fontWeight:700, fontFamily:"'Share Tech Mono',monospace",
                      background: fr.status==="triggered" ? "rgba(245,158,11,0.2)" : fr.status==="monitoring" ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.05)",
                      color: fr.status==="triggered" ? "#f59e0b" : fr.status==="monitoring" ? "#818cf8" : "#475569",
                    }}>{fr.status.toUpperCase()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ MISSION TIMELINE ═══ */}
        <div className="panel-glow" style={{ ...panelStyle, padding:"8px 16px" }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:6 }}>
            <div style={panelHeaderStyle}>🚀 MISSION TIMELINE — 450 DAY SURFACE STAY</div>
            <div style={{ fontSize:10, fontFamily:"'Share Tech Mono',monospace", color:"#94a3b8" }}>
              {((sol/450)*100).toFixed(1)}% COMPLETE · {450-sol} SOLS REMAINING
            </div>
          </div>
          <div style={{ position:"relative", height:20, background:"rgba(255,255,255,0.03)", borderRadius:4, overflow:"hidden" }}>
            <div style={{ position:"absolute", left:0, top:0, height:"100%", width:`${(sol/450)*100}%`, background:"linear-gradient(90deg, #10b981, #00e5ff)", borderRadius:4, transition:"width 1s", boxShadow:"0 0 10px rgba(0,229,255,0.3)" }} />
            {/* Markers */}
            {[
              { sol:1, label:"LANDING", color:"#10b981" },
              { sol:45, label:"FIRST HARVEST", color:"#3b82f6" },
              { sol:150, label:"FULL CAPACITY", color:"#a78bfa" },
              { sol:sol, label:`NOW (${sol})`, color:"#00e5ff" },
              { sol:350, label:"WIND DOWN", color:"#f59e0b" },
              { sol:450, label:"DEPARTURE", color:"#ef4444" },
            ].map((m,i) => (
              <div key={i} style={{ position:"absolute", left:`${(m.sol/450)*100}%`, top:0, height:"100%", display:"flex", flexDirection:"column", alignItems:"center", transform:"translateX(-50%)" }}>
                <div style={{ width:1, height:"100%", background:m.color, opacity:0.6 }} />
                <div style={{ position:"absolute", top:-1, fontSize:7, color:m.color, whiteSpace:"nowrap", fontFamily:"'Share Tech Mono',monospace", fontWeight:600, transform:"translateY(-100%)" }}>{m.label}</div>
              </div>
            ))}
          </div>
          <div style={{ display:"flex", justifyContent:"space-between", marginTop:4 }}>
            <span style={{ fontSize:8, color:"#475569", fontFamily:"'Share Tech Mono',monospace" }}>SOL 0</span>
            <span style={{ fontSize:8, color:"#475569", fontFamily:"'Share Tech Mono',monospace" }}>SOL 450</span>
          </div>
        </div>

        {/* RENT-A-HUMAN FOOTER */}
        <div style={{ display:"flex", gap:8 }}>
          <div className="panel-glow" style={{ ...panelStyle, flex:1, padding:"6px 12px", display:"flex", alignItems:"center", gap:10, background:"linear-gradient(90deg, rgba(236,72,153,0.04), transparent)" }}>
            <span style={{ fontSize:12 }}>🧑‍🔧</span>
            <div>
              <span style={{ fontSize:9, fontFamily:"'Orbitron',sans-serif", color:"#ec4899", letterSpacing:1 }}>RENT-A-HUMAN </span>
              <span style={{ fontSize:9, color:"#94a3b8", fontFamily:"'Share Tech Mono',monospace" }}>· PENDING: Manual inspection Zone B root system · Est: 12 min · Priority: MEDIUM</span>
            </div>
            <div style={{ marginLeft:"auto", display:"flex", gap:4 }}>
              <button style={{ padding:"3px 10px", fontSize:8, fontFamily:"'Orbitron',sans-serif", background:"rgba(16,185,129,0.15)", border:"1px solid rgba(16,185,129,0.3)", color:"#10b981", borderRadius:3, cursor:"pointer", letterSpacing:1 }}>ACCEPT</button>
              <button style={{ padding:"3px 10px", fontSize:8, fontFamily:"'Orbitron',sans-serif", background:"rgba(239,68,68,0.1)", border:"1px solid rgba(239,68,68,0.2)", color:"#ef4444", borderRadius:3, cursor:"pointer", letterSpacing:1 }}>DEFER</button>
            </div>
          </div>
          <div className="panel-glow" style={{ ...panelStyle, padding:"6px 12px", display:"flex", alignItems:"center", gap:8 }}>
            <span style={{ fontSize:9, fontFamily:"'Orbitron',sans-serif", color:"#06b6d4", letterSpacing:1 }}>🤖 SPOT-R7</span>
            <span style={{ fontSize:9, color:"#94a3b8", fontFamily:"'Share Tech Mono',monospace" }}>Zone A patrol · Battery: 78%</span>
            <StatusDot status="nominal" />
          </div>
          <div className="panel-glow" style={{ ...panelStyle, padding:"6px 12px", display:"flex", alignItems:"center", gap:6 }}>
            <span style={{ fontSize:8, fontFamily:"'Orbitron',sans-serif", color:"#64748b", letterSpacing:1 }}>ISRU SCOUT</span>
            <span style={{ fontSize:9, color:"#06b6d4", fontFamily:"'Share Tech Mono',monospace" }}>Ice deposit 2.3km NNW · ~340L</span>
          </div>
        </div>
      </div>
    </>
  );
}
