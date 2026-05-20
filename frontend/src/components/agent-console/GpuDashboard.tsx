import { useState, useEffect } from "react";
import { Cpu, Server, HardDrive, Flame, Zap, RotateCw, Terminal, Check, Settings } from "lucide-react";
import type { AppContent, Locale } from "../../i18n/content";

type GpuDashboardProps = {
  locale: Locale;
  t: AppContent;
};

type NodeInfo = {
  id: string;
  name: string;
  hardware: string;
  vram: string;
  load: number;
  temp: number;
  power: number;
  status: "active" | "idle" | "optimizing";
};

type ModelService = {
  id: string;
  name: string;
  node: string;
  vram: string;
  qps: number;
  latency: string;
  status: "normal" | "warning";
};

function GpuDashboard({ locale, t }: GpuDashboardProps) {
  const gx = t.console.gpu;

  // Active status states
  const [nodes, setNodes] = useState<NodeInfo[]>([
    {
      id: "node-1",
      name: "DromX-Compute-SXM-01",
      hardware: "8x NVIDIA H100 SXM5 80GB",
      vram: "512 / 640 GB",
      load: 84,
      temp: 68,
      power: 2.7,
      status: "active"
    },
    {
      id: "node-2",
      name: "DromX-Compute-PCI-02",
      hardware: "4x NVIDIA A100 PCIe 80GB",
      vram: "128 / 320 GB",
      load: 42,
      temp: 58,
      power: 1.1,
      status: "active"
    }
  ]);

  const [models] = useState<ModelService[]>([
    {
      id: "m1",
      name: "DeepSeek-V3 (8x 80GB)",
      node: "DromX-Compute-SXM-01",
      vram: "320 GB",
      qps: 142.4,
      latency: "1.2s",
      status: "normal"
    },
    {
      id: "m2",
      name: "Qwen-2.5-Coder-32B (1x 80GB)",
      node: "DromX-Compute-PCI-02",
      vram: "64 GB",
      qps: 48.1,
      latency: "0.6s",
      status: "normal"
    },
    {
      id: "m3",
      name: "Llama-3.1-70B (2x 80GB)",
      node: "DromX-Compute-SXM-01",
      vram: "140 GB",
      qps: 89.6,
      latency: "0.9s",
      status: "normal"
    }
  ]);

  const [logs, setLogs] = useState<string[]>([
    "[16:51:02] [SYSTEM] NVIDIA H100 GPU core cluster temperature stabilized at 68°C.",
    "[16:51:14] [DEEPSEEK] Context window allocation: 64k tokens optimized (VRAM saved: 12GB).",
    "[16:51:25] [QWEN] Batch processing triggered: 32 tasks completed successfully.",
    "[16:51:32] [ROUTING] LLM query distributed to SXM-01 Node (Response time: 480ms).",
    "[16:51:40] [SYSTEM] Periodic VRAM garbage collection complete. freed 8.4 GB."
  ]);

  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizeSuccess, setOptimizeSuccess] = useState(false);
  const [rebootingNode, setRebootingNode] = useState<string | null>(null);

  // Telemetry real-time updates simulation
  useEffect(() => {
    const timer = setInterval(() => {
      // Simulate slight fluctuations in metrics
      setNodes((prev) =>
        prev.map((node) => {
          if (node.status === "optimizing") return node;
          const loadDiff = Math.floor(Math.random() * 5) - 2; // -2 to +2
          const tempDiff = Math.floor(Math.random() * 3) - 1; // -1 to +1
          const powerDiff = Number((Math.random() * 0.2 - 0.1).toFixed(2));
          
          return {
            ...node,
            load: Math.min(100, Math.max(0, node.load + loadDiff)),
            temp: Math.min(95, Math.max(40, node.temp + tempDiff)),
            power: Number(Math.max(0.2, node.power + powerDiff).toFixed(1))
          };
        })
      );

      // Randomly append a telemetry log
      const logTemplates = [
        `[${new Date().toTimeString().split(" ")[0]}] [SYSTEM] Telemetry check: H100 clusters fully operational, power limits optimal.`,
        `[${new Date().toTimeString().split(" ")[0]}] [ROUTING] Dynamic load balancer successfully re-routed 18 inference tokens.`,
        `[${new Date().toTimeString().split(" ")[0]}] [VRAM] Allocated 4.2GB video memory for incoming JSON generation stream.`,
        `[${new Date().toTimeString().split(" ")[0]}] [SCHEDULER] Inference queue cleared. Total latency avg: 0.88s.`
      ];
      const randomLog = logTemplates[Math.floor(Math.random() * logTemplates.length)];
      setLogs((prev) => [randomLog, ...prev.slice(0, 14)]);
    }, 4000);

    return () => clearInterval(timer);
  }, []);

  const handleOptimizeVram = () => {
    setIsOptimizing(true);
    setOptimizeSuccess(false);

    // Simulate node VRAM optimization
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        status: "optimizing",
        load: Math.round(n.load / 2)
      }))
    );

    setTimeout(() => {
      setIsOptimizing(false);
      setOptimizeSuccess(true);
      setNodes((prev) =>
        prev.map((n) => ({
          ...n,
          status: "active",
          vram: n.id === "node-1" ? "428 / 640 GB" : "96 / 320 GB"
        }))
      );
      setLogs((prev) => [
        `[${new Date().toTimeString().split(" ")[0]}] [VRAM] Memory compaction successfully defragmented H100 and A100 caches!`,
        ...prev
      ]);
      setTimeout(() => setOptimizeSuccess(false), 3000);
    }, 2000);
  };

  const handleRebootNode = (nodeId: string, nodeName: string) => {
    setRebootingNode(nodeId);
    setNodes((prev) =>
      prev.map((n) => (n.id === nodeId ? { ...n, load: 0, status: "optimizing" } : n))
    );
    setLogs((prev) => [
      `[${new Date().toTimeString().split(" ")[0]}] [SYSTEM] Node ${nodeName} reboot command dispatched. Warm start triggered...`,
      ...prev
    ]);

    setTimeout(() => {
      setRebootingNode(null);
      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? {
                ...n,
                load: 40,
                status: "active"
              }
            : n
        )
      );
      setLogs((prev) => [
        `[${new Date().toTimeString().split(" ")[0]}] [SYSTEM] Node ${nodeName} warm reboot complete. Connected and operational.`,
        ...prev
      ]);
    }, 3000);
  };

  return (
    <div className="console-main gpu-shell" lang={locale}>
      <div className="skills-header" style={{ marginBottom: "20px" }}>
        <span className="section-label">
          {locale === "en" ? "Hardware Infrastructure" : "基础设施运营层"}
        </span>
        <h1 style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>{gx.title}</span>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className={`console-action ${optimizeSuccess ? "is-success" : "is-primary"}`}
              type="button"
              onClick={handleOptimizeVram}
              disabled={isOptimizing}
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "14px" }}
            >
              {isOptimizing ? (
                <RotateCw size={14} className="animate-spin" />
              ) : optimizeSuccess ? (
                <Check size={14} />
              ) : (
                <Settings size={14} />
              )}
              {optimizeSuccess
                ? locale === "en"
                  ? "VRAM Optimized!"
                  : "显存已优化！"
                : gx.actions.optimize}
            </button>
          </div>
        </h1>
        <p>{gx.subtitle}</p>
      </div>

      {/* GPU Overview Statistics Grid */}
      <div className="metrics-summary-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div className="skills-rail-card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(99, 102, 241, 0.15)", color: "rgb(129, 140, 248)" }}>
            <Cpu size={24} />
          </div>
          <div>
            <span style={{ display: "block", fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>{gx.globalUtilization}</span>
            <strong style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
              {isOptimizing ? "32.0%" : "63.0%"}
            </strong>
          </div>
        </div>

        <div className="skills-rail-card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(16, 185, 129, 0.15)", color: "rgb(52, 211, 153)" }}>
            <HardDrive size={24} />
          </div>
          <div>
            <span style={{ display: "block", fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>{gx.vramAllocation}</span>
            <strong style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
              {isOptimizing ? "556 / 960 GB" : "640 / 960 GB"}
            </strong>
          </div>
        </div>

        <div className="skills-rail-card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(245, 158, 11, 0.15)", color: "rgb(251, 191, 36)" }}>
            <Zap size={24} />
          </div>
          <div>
            <span style={{ display: "block", fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>{gx.powerConsumption}</span>
            <strong style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
              {isOptimizing ? "1.8 kW" : "3.8 kW"}
            </strong>
          </div>
        </div>

        <div className="skills-rail-card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(239, 68, 68, 0.15)", color: "rgb(248, 113, 113)" }}>
            <Flame size={24} />
          </div>
          <div>
            <span style={{ display: "block", fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>{gx.temperature}</span>
            <strong style={{ fontSize: "20px", fontWeight: 700, color: "var(--text-primary)" }}>
              {isOptimizing ? "52°C" : "63°C"}
            </strong>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "20px" }}>
        
        {/* Node Cards and Running Services */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <section className="console-section" style={{ width: "100%", padding: "20px" }}>
            <div className="section-header" style={{ marginBottom: "16px" }}>
              <div>
                <span className="section-label">{gx.nodeHealth}</span>
                <h2>{gx.activeNodes}</h2>
              </div>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {nodes.map((node) => (
                <div
                  key={node.id}
                  style={{
                    padding: "16px",
                    border: "1px solid var(--border-color)",
                    borderRadius: "8px",
                    background: "rgba(255, 255, 255, 0.02)",
                    position: "relative",
                    overflow: "hidden"
                  }}
                >
                  {/* Subtle pulsing green light inside card */}
                  <div
                    style={{
                      position: "absolute",
                      top: "16px",
                      right: "16px",
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: node.status === "optimizing" ? "#f59e0b" : "#10b981",
                      boxShadow: node.status === "optimizing" ? "0 0 8px #f59e0b" : "0 0 8px #10b981"
                    }}
                  />
                  
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                    <div>
                      <h3 style={{ fontSize: "15px", fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                        <Server size={15} style={{ color: "var(--text-muted)" }} />
                        {node.name}
                      </h3>
                      <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{node.hardware}</span>
                    </div>
                    <button
                      className="console-action"
                      type="button"
                      disabled={rebootingNode === node.id || node.status === "optimizing"}
                      onClick={() => handleRebootNode(node.id, node.name)}
                      style={{ padding: "4px 8px", fontSize: "11px", display: "flex", alignItems: "center", gap: "4px" }}
                    >
                      {rebootingNode === node.id ? (
                        <RotateCw size={11} className="animate-spin" />
                      ) : (
                        <RotateCw size={11} />
                      )}
                      {gx.actions.reboot}
                    </button>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", fontSize: "13px" }}>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", fontSize: "11px" }}>VRAM Load</span>
                      <strong style={{ color: "var(--text-primary)" }}>{node.vram}</strong>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", fontSize: "11px" }}>GPU Temp</span>
                      <strong style={{ color: node.temp > 70 ? "rgb(248, 113, 113)" : "var(--text-primary)" }}>{node.temp}°C</strong>
                    </div>
                    <div>
                      <span style={{ color: "var(--text-muted)", display: "block", fontSize: "11px" }}>Power</span>
                      <strong style={{ color: "var(--text-primary)" }}>{node.power} kW</strong>
                    </div>
                  </div>

                  {/* Telemetry percentage bar */}
                  <div style={{ marginTop: "14px", height: "4px", background: "rgba(255, 255, 255, 0.05)", borderRadius: "2px" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${node.load}%`,
                        background: node.load > 80 ? "rgb(248, 113, 113)" : "rgb(129, 140, 248)",
                        borderRadius: "2px",
                        transition: "width 1s ease"
                      }}
                    />
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginTop: "4px", color: "var(--text-muted)" }}>
                    <span>Utilization</span>
                    <strong>{node.load}%</strong>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="console-section" style={{ width: "100%", padding: "20px" }}>
            <div className="section-header" style={{ marginBottom: "16px" }}>
              <div>
                <span className="section-label">Active Deployments</span>
                <h2>{gx.runningModels}</h2>
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)" }}>
                    <th style={{ padding: "8px 4px" }}>Model Name</th>
                    <th style={{ padding: "8px 4px" }}>Host Cluster</th>
                    <th style={{ padding: "8px 4px" }}>Memory</th>
                    <th style={{ padding: "8px 4px" }}>Queries</th>
                    <th style={{ padding: "8px 4px" }}>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((model) => (
                    <tr key={model.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                      <td style={{ padding: "10px 4px", fontWeight: 600, color: "var(--text-primary)" }}>{model.name}</td>
                      <td style={{ padding: "10px 4px", color: "var(--text-muted)" }}>{model.node.split("-").pop()}</td>
                      <td style={{ padding: "10px 4px" }}>{model.vram}</td>
                      <td style={{ padding: "10px 4px" }}>{model.qps} / s</td>
                      <td style={{ padding: "10px 4px", color: "rgb(52, 211, 153)" }}>{model.latency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* Real-time Telemetry Live Log Stream */}
        <section className="console-section" style={{ display: "flex", flexDirection: "column", padding: "20px" }}>
          <div className="section-header" style={{ marginBottom: "12px" }}>
            <div>
              <span className="section-label" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <Terminal size={12} />
                Live Log Stream
              </span>
              <h2>{gx.logs}</h2>
            </div>
          </div>

          <div
            style={{
              flex: 1,
              background: "rgba(0,0,0,0.25)",
              border: "1px solid var(--border-color)",
              borderRadius: "6px",
              padding: "12px",
              fontFamily: "monospace",
              fontSize: "11px",
              lineHeight: "1.6",
              color: "rgba(255, 255, 255, 0.75)",
              overflowY: "auto",
              maxHeight: "480px"
            }}
          >
            {logs.map((log, index) => (
              <div
                key={index}
                style={{
                  marginBottom: "6px",
                  color: log.includes("[SYSTEM]")
                    ? "#818cf8"
                    : log.includes("[VRAM]")
                    ? "#34d399"
                    : "inherit",
                  whiteSpace: "pre-wrap",
                  animation: index === 0 ? "fadeInLog 0.3s ease-out" : "none"
                }}
              >
                {log}
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Embedded CSS animation for log insertion */}
      <style>{`
        @keyframes fadeInLog {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-spin {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default GpuDashboard;
