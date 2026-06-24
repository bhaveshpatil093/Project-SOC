# ISRO SOC Platform — Official Performance Baseline

**Benchmark Date:** [YYYY-MM-DD]
**Environment:** Staging (specs: [CPU/RAM/disk specs])
**Test Data Volume:** [N] documents across 3 log sources

## Ingestion Performance
| Batch Size | Throughput (docs/sec) | p95 Latency |
|-----------|------------------------|-------------|
| 100       | XXX                    | XXms        |
| 1000      | XXX                    | XXms        |
| 5000      | XXX                    | XXms        |

## Feature Pipeline Performance
| Entity Count | Processing Time | Throughput |
|--------------|------------------|------------|
| 10           | XXms             | XXX/sec    |
| 100          | XXms             | XXX/sec    |
| 1000         | XXms             | XXX/sec    |

## ML Inference Latency
| Model | p50 | p95 | p99 |
|-------|-----|-----|-----|
| Isolation Forest | Xms | Xms | Xms |
| Autoencoder | Xms | Xms | Xms |
| LSTM | Xms | Xms | Xms |
| Full Ensemble | Xms | Xms | Xms |

## SLM Response Time
| Query Type | Time to First Token | Total Response Time |
|-----------|----------------------|----------------------|
| Simple explanation | Xs | Xs |
| Multi-tool investigation | Xs | Xs |

## API Endpoint Latency (No Load)
| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| `/api/alerts` | Xms | Xms | Xms |
| `/api/incidents` | Xms | Xms | Xms |
| `/api/slm/status` | Xms | Xms | Xms |

## Concurrent Capacity
- **Maximum analysts before SLA degradation**: [N] concurrent users
- **Bottleneck identified**: [ES / SLM inference / DB connections]

## Recommended Production Specs
Based on this baseline, for a SOC team of [N] analysts:
- **CPU**: X cores minimum
- **RAM**: X GB minimum (SLM is the largest consumer)
- **Disk**: X GB/month log retention estimate
- **Network**: X Mbps for log ingestion volume

## Scaling Recommendations
- **At 2x current log volume**: [specific recommendation]
- **At 5x current log volume**: [specific recommendation]
- **SLM bottleneck mitigation**: [GPU acceleration recommendation if applicable]
