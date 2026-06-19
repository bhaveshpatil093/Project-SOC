import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, Filter as FilterIcon } from 'lucide-react';
import { useUiStore } from '../../store/uiStore';
import { THEMES } from '../../utils/theme';

export const CorrelationGraph = React.memo(({ incidents = [], alerts = [], maxNodes = 500, onNodeClick }) => {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const canvasRef = useRef(null);
  const navigate = useNavigate();

  const [minLevel, setMinLevel] = useState('all');
  const [onlyIncidents, setOnlyIncidents] = useState(false);
  const [simulation, setSimulation] = useState(null);
  const [tooltip, setTooltip] = useState({ show: false, x: 0, y: 0, content: null });
  const { theme } = useUiStore();
  const colors = THEMES[theme];

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

    const useCanvas = graphData.nodes.length > 100;

    const svg = d3.select(svgRef.current);
    const canvas = canvasRef.current;
    
    svg.selectAll("*").remove();
    const context = canvas ? canvas.getContext("2d") : null;

    if (useCanvas && canvas) {
      canvas.width = width;
      canvas.height = height;
      svg.style("display", "none");
      d3.select(canvas).style("display", "block");
    } else {
      if (canvas) d3.select(canvas).style("display", "none");
      svg.style("display", "block");
    }

    // Setup zoom
    let transform = d3.zoomIdentity;
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (e) => {
        transform = e.transform;
        if (useCanvas) tick(); // manually re-render canvas on zoom
        else svg.select("g").attr("transform", e.transform);
      });
      
    if (useCanvas) {
      d3.select(canvas).call(zoom);
    } else {
      svg.call(zoom);
    }

    const g = useCanvas ? null : svg.append("g");

    // Deep copy for D3
    const nodes = graphData.nodes.map(d => Object.create(d));
    const links = graphData.links.map(d => Object.create(d));

    // Throttle force simulation ticks with alpha decay = 0.02
    const sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(60))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(d => d.radius + 10))
      .alphaDecay(0.02);

    setSimulation(sim);

    let linkElements, nodeElements;

    if (!useCanvas) {
      // Draw Links (SVG)
      linkElements = g.append("g")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", d => {
          if (d.type === 'alert-incident') return colors.critical; 
          if (d.type === 'alert-alert') return colors.high; 
          return colors.border; 
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

      // Draw Nodes (SVG)
      nodeElements = g.append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));

      // Shapes
      nodeElements.each(function(d) {
        const el = d3.select(this);
        if (d.type === 'incident') {
          el.append("path")
            .attr("d", hexPath(d.radius))
            .attr("fill", colors.critical + '33') // 20% opacity
            .attr("stroke", colors.critical)
            .attr("stroke-width", 2);
        } else {
          el.append("circle")
            .attr("r", d.radius)
            .attr("fill", d => {
              if (d.type === 'host') return colors.accent + '33';
              if (d.type === 'user') return '#8b5cf633'; // light purple
              if (d.type === 'alert') {
                if (d.score >= 0.8) return colors.critical + '33';
                if (d.score >= 0.6) return colors.high + '33';
                if (d.score >= 0.4) return colors.medium + '33';
                return colors.low + '33';
              }
              return colors.bg_tertiary;
            })
            .attr("stroke", d => {
              if (d.type === 'host') return colors.accent;
              if (d.type === 'user') return '#8b5cf6';
              if (d.type === 'alert') {
                if (d.score >= 0.8) return colors.critical;
                if (d.score >= 0.6) return colors.high;
                if (d.score >= 0.4) return colors.medium;
                return colors.low;
              }
              return colors.border;
            })
            .attr("stroke-width", 2);
        }
      });

      // Labels
      nodeElements.append("text")
        .attr("x", d => d.radius + 5)
        .attr("y", 4)
        .text(d => d.label)
        .attr("font-size", "10px")
        .attr("fill", colors.text_secondary)
        .attr("font-family", "monospace")
        .attr("pointer-events", "none");

      nodeElements.on("mouseover", (event, d) => {
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
          .attr("stroke", d.type === 'incident' ? colors.critical : (
            d.type === 'host' ? colors.accent :
            d.type === 'user' ? '#8b5cf6' :
            d.score >= 0.8 ? colors.critical :
            d.score >= 0.6 ? colors.high : 
            d.score >= 0.4 ? colors.medium : colors.low
          ));
      })
      .on("click", (event, d) => {
        if (onNodeClick) {
          onNodeClick(d);
        } else {
          if (d.type === 'alert') navigate(`/alerts/${d.id}`);
          if (d.type === 'incident') navigate(`/incidents`);
        }
      });
    } else {
      // Canvas interaction handlers
      d3.select(canvas)
        .call(d3.drag()
          .container(canvas)
          .subject(event => {
            const [x, y] = transform.invert([event.x, event.y]);
            return sim.find(x, y, 30);
          })
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));
    }

    function tick() {
      if (useCanvas && context) {
        context.save();
        context.clearRect(0, 0, width, height);
        context.translate(transform.x, transform.y);
        context.scale(transform.k, transform.k);
        
        // Draw links
        context.globalAlpha = 0.6;
        links.forEach(d => {
          context.beginPath();
          context.moveTo(d.source.x, d.source.y);
          context.lineTo(d.target.x, d.target.y);
          if (d.type === 'alert-incident') {
            context.strokeStyle = colors.critical;
            context.lineWidth = 3;
            context.setLineDash([]);
          } else if (d.type === 'alert-alert') {
            context.strokeStyle = colors.high;
            context.lineWidth = 1.5;
            context.setLineDash([4, 4]);
          } else {
            context.strokeStyle = colors.border;
            context.lineWidth = 1.5;
            context.setLineDash([]);
          }
          context.stroke();
        });
        
        // Draw nodes
        context.globalAlpha = 1.0;
        context.setLineDash([]);
        nodes.forEach(d => {
          context.beginPath();
          if (d.type === 'incident') {
            const a = (2 * Math.PI) / 6;
            for (let i = 0; i < 6; i++) {
              const x = d.x + d.radius * Math.sin(a * i);
              const y = d.y - d.radius * Math.cos(a * i);
              if (i === 0) context.moveTo(x, y);
              else context.lineTo(x, y);
            }
            context.closePath();
            context.fillStyle = colors.critical + '33';
            context.strokeStyle = colors.critical;
            context.lineWidth = 2;
          } else {
            context.arc(d.x, d.y, d.radius, 0, 2 * Math.PI);
            if (d.type === 'host') { context.fillStyle = colors.accent + '33'; context.strokeStyle = colors.accent; }
            else if (d.type === 'user') { context.fillStyle = '#8b5cf633'; context.strokeStyle = '#8b5cf6'; }
            else if (d.type === 'alert') {
              if (d.score >= 0.8) { context.fillStyle = colors.critical + '33'; context.strokeStyle = colors.critical; }
              else if (d.score >= 0.6) { context.fillStyle = colors.high + '33'; context.strokeStyle = colors.high; }
              else if (d.score >= 0.4) { context.fillStyle = colors.medium + '33'; context.strokeStyle = colors.medium; }
              else { context.fillStyle = colors.low + '33'; context.strokeStyle = colors.low; }
            } else {
              context.fillStyle = colors.bg_tertiary; context.strokeStyle = colors.border;
            }
            context.lineWidth = 2;
          }
          context.fill();
          context.stroke();
          
          // Labels
          context.fillStyle = colors.text_secondary;
          context.font = "10px monospace";
          context.fillText(d.label, d.x + d.radius + 5, d.y + 4);
        });
        
        context.restore();
      } else if (!useCanvas) {
        linkElements
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);
        nodeElements.attr("transform", d => `translate(${d.x},${d.y})`);
      }
    }

    sim.on("tick", tick);

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
  }, [graphData, navigate, onNodeClick, colors]);

  const handleResetLayout = () => {
    if (simulation) {
      simulation.alpha(1).restart();
    }
  };

  return (
    <div className="relative w-full h-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-xl overflow-hidden shadow-inner flex flex-col">
      
      {/* Controls Overlay */}
      <div className="absolute top-4 right-4 z-10 bg-[var(--bg_primary)]/80 backdrop-blur border border-[var(--border)] p-3 rounded-lg flex flex-col gap-3 shadow-lg">
        <div className="flex items-center gap-2 text-[var(--text_secondary)] text-xs">
          <FilterIcon className="h-4 w-4 text-blue-500" />
          <select 
            className="bg-[var(--bg_secondary)] border border-[var(--border)] rounded px-2 py-1 outline-none"
            value={minLevel} onChange={e => setMinLevel(e.target.value)}
          >
            <option value="all">All Levels</option>
            <option value="medium">Medium+</option>
            <option value="high">High+</option>
            <option value="critical">Critical Only</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-xs text-[var(--text_secondary)] cursor-pointer">
          <input type="checkbox" checked={onlyIncidents} onChange={e => setOnlyIncidents(e.target.checked)} className="accent-blue-500" />
          Only Incidents & Entities
        </label>
        <button onClick={handleResetLayout} className="flex items-center justify-center gap-2 bg-[var(--bg_secondary)] hover:bg-[var(--bg_tertiary)] text-xs text-[var(--text_primary)] px-3 py-1.5 rounded transition-colors border border-[var(--border)]">
          <RefreshCw className="h-3 w-3" /> Reset Layout
        </button>
        <div className="text-[10px] text-[var(--text_secondary)] mt-1 text-center font-mono">
          Showing {graphData.nodes.length} nodes, {graphData.links.length} edges
        </div>
      </div>

      {/* Rendering Container */}
      <div ref={containerRef} className="flex-1 w-full h-full cursor-grab active:cursor-grabbing relative">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ display: 'none' }}></canvas>
        <svg ref={svgRef} className="absolute inset-0 w-full h-full"></svg>
      </div>

      {/* Tooltip */}
      {tooltip.show && (
        <div 
          className="fixed z-50 bg-[var(--bg_primary)] border border-[var(--border)] text-[var(--text_primary)] text-xs rounded shadow-2xl p-3 pointer-events-none transform -translate-x-1/2 -translate-y-full mt-[-10px]"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="font-bold mb-1 border-b border-[var(--border)] pb-1 uppercase tracking-wider">{tooltip.content.type}</p>
          <p className="font-mono text-blue-400 mb-1 break-all max-w-[200px]">{tooltip.content.id}</p>
          {tooltip.content.score !== undefined && <p>Score: {(tooltip.content.score * 100).toFixed(0)}</p>}
          {tooltip.content.tactic && <p>Tactic: {tooltip.content.tactic}</p>}
        </div>
      )}
    </div>
  );
});
