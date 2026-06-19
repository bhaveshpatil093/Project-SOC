import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Filter as FilterIcon } from 'lucide-react';

export const CorrelationGraph = ({ incidents = [], alerts = [], maxNodes = 50, onNodeClick }) => {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const navigate = useNavigate();

  const [minLevel, setMinLevel] = useState('all');
  const [onlyIncidents, setOnlyIncidents] = useState(false);
  const [simulation, setSimulation] = useState(null);
  const [tooltip, setTooltip] = useState({ show: false, x: 0, y: 0, content: null });

  // Data processing to graph representation
  const graphData = useMemo(() => {
    const nodesMap = new Map();
    const links = [];

    // Filter logic
    const filterLevelScore = { 'all': 0, 'low': 0, 'medium': 0.4, 'high': 0.6, 'critical': 0.8 };
    const threshold = filterLevelScore[minLevel];

    const processedIncidents = incidents.filter(i => i.incident_threat_score >= threshold);
    const processedAlerts = alerts.filter(a => !onlyIncidents && a.threat_score >= threshold);

    // Extract nodes and edges
    processedIncidents.forEach(inc => {
      if (!nodesMap.has(inc.incident_id)) {
        nodesMap.set(inc.incident_id, {
          id: inc.incident_id,
          type: 'incident',
          label: 'INCIDENT',
          detail: inc.entity_key,
          score: inc.incident_threat_score,
          radius: 24,
          data: inc
        });
      }

      // Extract Entities
      if (inc.host_id && !nodesMap.has(inc.host_id)) {
        nodesMap.set(inc.host_id, {
          id: inc.host_id, type: 'host', label: inc.host_id, radius: 16
        });
      }
      if (inc.user_name && !nodesMap.has(inc.user_name)) {
        nodesMap.set(inc.user_name, {
          id: inc.user_name, type: 'user', label: inc.user_name, radius: 14
        });
      }
    });

    processedAlerts.forEach(al => {
      if (!nodesMap.has(al.id)) {
        nodesMap.set(al.id, {
          id: al.id,
          type: 'alert',
          label: al.id.substring(0, 6) + '...',
          score: al.threat_score,
          tactic: al.mitre_tactic,
          time: new Date(al.timestamp).getTime(),
          radius: 12,
          data: al
        });
      }
      if (al.host_id && !nodesMap.has(al.host_id)) {
        nodesMap.set(al.host_id, { id: al.host_id, type: 'host', label: al.host_id, radius: 16 });
      }
      if (al.user_name && !nodesMap.has(al.user_name)) {
        nodesMap.set(al.user_name, { id: al.user_name, type: 'user', label: al.user_name, radius: 14 });
      }
    });

    // Extract Edges
    processedIncidents.forEach(inc => {
      (inc.alert_ids || []).forEach(a_id => {
        if (nodesMap.has(a_id)) {
          links.push({ source: a_id, target: inc.incident_id, type: 'alert-incident' });
        }
      });
    });

    processedAlerts.forEach(al => {
      if (al.host_id && nodesMap.has(al.host_id)) {
        links.push({ source: al.host_id, target: al.id, type: 'host-alert' });
      }
      if (al.user_name && nodesMap.has(al.user_name)) {
        links.push({ source: al.user_name, target: al.id, type: 'user-alert' });
      }
    });

    // Alert to Alert correlation
    const alertNodes = Array.from(nodesMap.values()).filter(n => n.type === 'alert');
    for (let i = 0; i < alertNodes.length; i++) {
      for (let j = i + 1; j < alertNodes.length; j++) {
        const a1 = alertNodes[i];
        const a2 = alertNodes[j];
        if (a1.tactic && a1.tactic === a2.tactic) {
          const timeDiff = Math.abs(a1.time - a2.time) / (1000 * 60);
          if (timeDiff <= 15) {
            links.push({ source: a1.id, target: a2.id, type: 'alert-alert' });
          }
        }
      }
    }

    let nodes = Array.from(nodesMap.values());
    
    // Performance Guard Cluster
    if (nodes.length > maxNodes) {
      console.warn(`Graph nodes (${nodes.length}) > ${maxNodes}. Proceeding with subset.`);
      // Just slice for basic safety or aggregate (complex logic skipped for simplicity, slicing by severity)
      nodes.sort((a, b) => (b.score || 0) - (a.score || 0));
      const keepIds = new Set(nodes.slice(0, maxNodes).map(n => n.id));
      nodes = nodes.filter(n => keepIds.has(n.id));
      for (let i = links.length - 1; i >= 0; i--) {
        if (!keepIds.has(links[i].source) || !keepIds.has(links[i].target)) {
          links.splice(i, 1);
        }
      }
    }

    return { nodes, links };
  }, [incidents, alerts, minLevel, onlyIncidents, maxNodes]);

  useEffect(() => {
    if (!containerRef.current) return;
    
    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Setup zoom
    const g = svg.append("g");
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    // Deep copy for D3
    const nodes = graphData.nodes.map(d => Object.create(d));
    const links = graphData.links.map(d => Object.create(d));

    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(60))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(d => d.radius + 10));

    setSimulation(sim);

    // Draw Links
    const link = g.append("g")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", d => {
        if (d.type === 'alert-incident') return '#ef4444'; // red
        if (d.type === 'alert-alert') return '#f97316'; // orange
        return '#475569'; // slate-600
      })
      .attr("stroke-width", d => d.type === 'alert-incident' ? 3 : 1.5)
      .attr("stroke-dasharray", d => d.type === 'alert-alert' ? "4,4" : "none");

    // Hexagon path generator
    const hexPath = (r) => {
      const a = (2 * Math.PI) / 6;
      let path = "";
      for (let i = 0; i < 6; i++) {
        const x = r * Math.sin(a * i);
        const y = -r * Math.cos(a * i);
        path += (i === 0 ? "M" : "L") + x + "," + y;
      }
      path += "Z";
      return path;
    };

    // Draw Nodes
    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Shapes
    node.each(function(d) {
      const el = d3.select(this);
      if (d.type === 'incident') {
        el.append("path")
          .attr("d", hexPath(d.radius))
          .attr("fill", "#7f1d1d")
          .attr("stroke", "#ef4444")
          .attr("stroke-width", 2);
      } else {
        el.append("circle")
          .attr("r", d.radius)
          .attr("fill", d => {
            if (d.type === 'host') return '#1e3a8a';
            if (d.type === 'user') return '#4c1d95';
            if (d.type === 'alert') {
              if (d.score >= 0.8) return '#991b1b';
              if (d.score >= 0.6) return '#9a3412';
              if (d.score >= 0.4) return '#854d0e';
              return '#1e40af';
            }
            return '#334155';
          })
          .attr("stroke", d => {
            if (d.type === 'host') return '#3b82f6';
            if (d.type === 'user') return '#8b5cf6';
            if (d.type === 'alert') {
              if (d.score >= 0.8) return '#ef4444';
              if (d.score >= 0.6) return '#f97316';
              return '#3b82f6';
            }
            return '#64748b';
          })
          .attr("stroke-width", 2);
      }
    });

    // Labels
    node.append("text")
      .attr("x", d => d.radius + 5)
      .attr("y", 4)
      .text(d => d.label)
      .attr("font-size", "10px")
      .attr("fill", "#94a3b8")
      .attr("font-family", "monospace")
      .attr("pointer-events", "none");

    node.on("mouseover", (event, d) => {
      setTooltip({
        show: true,
        x: event.pageX,
        y: event.pageY,
        content: d
      });
      d3.select(event.currentTarget).select("circle, path")
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 3);
    })
    .on("mouseout", (event, d) => {
      setTooltip({ show: false, x: 0, y: 0, content: null });
      d3.select(event.currentTarget).select("circle, path")
        .attr("stroke-width", 2)
        .attr("stroke", d.type === 'incident' ? "#ef4444" : (
          d.type === 'host' ? '#3b82f6' :
          d.type === 'user' ? '#8b5cf6' :
          d.score >= 0.8 ? '#ef4444' :
          d.score >= 0.6 ? '#f97316' : '#3b82f6'
        ));
    })
    .on("click", (event, d) => {
      if (onNodeClick) {
        onNodeClick(d);
      } else {
        if (d.type === 'alert') navigate(`/alerts/${d.id}`);
        if (d.type === 'incident') navigate(`/incidents`); // or detail if route existed
      }
    });

    sim.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag handlers
    function dragstarted(event) {
      if (!event.active) sim.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }
    
    function dragged(event) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }
    
    function dragended(event) {
      if (!event.active) sim.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => {
      sim.stop();
    };
  }, [graphData, navigate, onNodeClick]);

  const handleResetLayout = () => {
    if (simulation) {
      simulation.alpha(1).restart();
    }
  };

  return (
    <div className="relative w-full h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner flex flex-col">
      
      {/* Controls Overlay */}
      <div className="absolute top-4 right-4 z-10 bg-slate-900/80 backdrop-blur border border-slate-700 p-3 rounded-lg flex flex-col gap-3 shadow-lg">
        <div className="flex items-center gap-2 text-slate-300 text-xs">
          <FilterIcon className="h-4 w-4 text-blue-500" />
          <select 
            className="bg-slate-800 border border-slate-700 rounded px-2 py-1 outline-none"
            value={minLevel} onChange={e => setMinLevel(e.target.value)}
          >
            <option value="all">All Levels</option>
            <option value="medium">Medium+</option>
            <option value="high">High+</option>
            <option value="critical">Critical Only</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
          <input type="checkbox" checked={onlyIncidents} onChange={e => setOnlyIncidents(e.target.checked)} className="accent-blue-500" />
          Only Incidents & Entities
        </label>
        <button onClick={handleResetLayout} className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-xs text-white px-3 py-1.5 rounded transition-colors border border-slate-600">
          <RefreshCw className="h-3 w-3" /> Reset Layout
        </button>
        <div className="text-[10px] text-slate-500 mt-1 text-center font-mono">
          Showing {graphData.nodes.length} nodes, {graphData.links.length} edges
        </div>
      </div>

      {/* SVG Container */}
      <div ref={containerRef} className="flex-1 w-full h-full cursor-grab active:cursor-grabbing">
        <svg ref={svgRef} className="w-full h-full"></svg>
      </div>

      {/* Tooltip */}
      {tooltip.show && (
        <div 
          className="fixed z-50 bg-slate-900 border border-slate-700 text-white text-xs rounded shadow-2xl p-3 pointer-events-none transform -translate-x-1/2 -translate-y-full mt-[-10px]"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="font-bold mb-1 border-b border-slate-800 pb-1 uppercase tracking-wider">{tooltip.content.type}</p>
          <p className="font-mono text-blue-400 mb-1 break-all max-w-[200px]">{tooltip.content.id}</p>
          {tooltip.content.score !== undefined && <p>Score: {(tooltip.content.score * 100).toFixed(0)}</p>}
          {tooltip.content.tactic && <p>Tactic: {tooltip.content.tactic}</p>}
        </div>
      )}
    </div>
  );
};
