from prometheus_client import Counter, Histogram, Gauge, Info

# Counters
alerts_scored_total = Counter(
    "soc_alerts_scored_total",
    "Total alerts scored by threat level",
    ["threat_level"]
)
feedback_submitted_total = Counter(
    "soc_feedback_total", 
    "Total analyst feedback submissions", 
    ["label"]
)
slm_queries_total = Counter(
    "soc_slm_queries_total", 
    "Total SLM chat queries", 
    ["question_type"]
)
pipeline_errors_total = Counter(
    "soc_pipeline_errors_total", 
    "Pipeline errors by stage",
    ["stage"]  # ingestion/features/scoring/slm
)

# Histograms
scoring_cycle_duration = Histogram(
    "soc_scoring_cycle_duration_seconds",
    "Time taken per scoring cycle",
    buckets=[1, 5, 10, 30, 60, 120]
)
slm_inference_duration = Histogram(
    "soc_slm_inference_duration_seconds",
    "SLM inference time per query",
    buckets=[1, 5, 10, 30, 60]
)
es_query_duration = Histogram(
    "soc_es_query_duration_seconds",
    "Elasticsearch query duration",
    ["operation"],  # fetch/index/search
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Gauges
open_alerts_gauge = Gauge("soc_open_alerts", "Current open alert count")
critical_alerts_gauge = Gauge("soc_critical_alerts", "Current critical alert count")
model_loaded_gauge = Gauge(
    "soc_model_loaded", "Whether each model is loaded", ["model_name"]
)
entity_risk_max_gauge = Gauge("soc_entity_risk_max", "Highest entity risk score")
