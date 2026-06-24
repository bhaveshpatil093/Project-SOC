# Model Card: Fine-Tuned Investigation Assistant (Phi-3-mini)

## Model Details
- **Architecture**: Transformer-based Causal Language Model (Phi-3-mini-4k-instruct)
- **Version**: tracked via MLflow (ISRO-SOC-v1.2)
- **Input**: RAG-augmented Text Prompts (Markdown/Plaintext)
- **Output**: Generative Markdown text explaining incidents and alerts
- **Training data**: Base model from Microsoft, Fine-tuned locally on 10,000+ ISRO historical incident resolutions and SIEM manual playbooks.

## Intended Use
Operates as the primary natural-language interface for Tier 1 SOC analysts. It summarizes raw log JSON, explains complex SHAP feature anomalies, and suggests immediate remediation steps based on ISRO-specific historical context retrieved from ChromaDB.

## Training Data
- **Base Model**: Microsoft Phi-3-mini
- **Fine-Tuning Source**: Hand-labeled `soc-analyst-feedback` records and resolved `soc-incidents` from the past 2 years.
- **Data Pruning**: All IP addresses, hostnames, and user IDs were systematically scrubbed and replaced with generic tokens during the fine-tuning phase to prevent memorization of hardcoded infrastructure.

## Performance Metrics
- **Last evaluated**: During SLM pre-deployment phase
- **BLEU/ROUGE Scores**: 0.88 / 0.85
- **Hallucination Rate**: < 3% (Verified via `test_slm_quality.py`)
- **Average Generation Time**: ~1.5s per response (RTX 4090)

## Ethical Considerations
- **Hallucination Risk**: Large language models can confidently state incorrect information. The platform mitigates this by aggressively grounding the model using strict RAG context limits (only injecting 3 historical alerts at a time).
- **Automation Bias**: Analysts may become over-reliant on the AI's conclusions. Disclaimers are rendered in the UI reminding users that they hold ultimate triage authority.

## Limitations
- Model max token length is 4096. Extremely large log files will be aggressively truncated, potentially blinding the model to context at the end of the payload.
- Does not possess internet access; it cannot dynamically research novel CVEs published after its fine-tuning date unless the context is explicitly passed via the RAG pipeline.

## Retraining
- **Automatic**: None. (Base model weights are frozen in production).
- **Manual**: Triggered manually by ML Engineers executing `make finetune`.
