import argparse
import logging
import os

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments

try:
    from trl import SFTTrainer
except ImportError:
    pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models/saved/phi3-soc-finetuned"))
DATASET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "training_data/soc_finetune.jsonl"))
SOC_SYSTEM_PROMPT = "You are an expert cybersecurity analyst assistant for the ISRO ISTRAC SOC team.\nYou help Level-1 SOC engineers investigate security alerts.\nYou have access to alert details, SHAP feature importance, MITRE ATT&CK context,\nand historical alert data. Always be precise, concise, and actionable.\nFormat responses as: Summary -> Evidence -> Recommended Action.\nNever make up data - only use what is provided in context."

# QLoRA config
LORA_CONFIG = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

# BitsAndBytes 4-bit config
BNB_CONFIG = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

# Training arguments
TRAINING_ARGS = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_steps=50,
    eval_steps=50,
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
    report_to="none"
)

def format_sample_for_training(sample: dict) -> dict:
    # Formats {instruction, input, output} explicitly mapped as Phi-3 chat template boundaries
    prompt = f"<|system|>\n{SOC_SYSTEM_PROMPT}<|end|>\n"
    prompt += f"<|user|>\n{sample.get('instruction', '')}\n{sample.get('input', '')}<|end|>\n"
    prompt += f"<|assistant|>\n{sample.get('output', '')}<|end|>\n"
    return {"text": prompt}

def load_and_prepare_dataset(path: str):
    logger.info(f"Loading dataset directly mapping bounds from {path}")
    raw_dataset = load_dataset("json", data_files=path, split="train")

    # Apply format_sample_for_training cleanly avoiding implicit column clashes
    formatted_dataset = raw_dataset.map(format_sample_for_training, remove_columns=raw_dataset.column_names)

    # 90/10 train/eval split
    split_dataset = formatted_dataset.train_test_split(test_size=0.1, seed=42)
    return split_dataset

def run_finetuning(dry_run=False):
    has_gpu = torch.cuda.is_available()

    model_name = MODEL_NAME
    bnb_config = BNB_CONFIG
    fp16 = True

    if not has_gpu:
        logger.warning("No CUDA GPU detected! Falling back to TinyLlama fp32 full tuning bounds.")
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        bnb_config = None
        fp16 = False
        TRAINING_ARGS.fp16 = False
        LORA_CONFIG.target_modules = ["q_proj", "v_proj"]

    logger.info(f"Targeting native model architecture: {model_name}")

    # 1. Dataset Prep
    if not os.path.exists(DATASET_PATH):
        logger.error(f"Dataset not found strictly bound at {DATASET_PATH}.")
        return

    dataset = load_and_prepare_dataset(DATASET_PATH)
    logger.info(f"Train split size strictly bounded: {len(dataset['train'])}")
    logger.info(f"Eval split size strictly bounded: {len(dataset['test'])}")

    if dry_run:
        logger.info("Dry run enabled. Safely printing explicit generation format sample 0:")
        print(dataset['train'][0]['text'])
        logger.info("Dry run natively completed. Exiting securely.")
        return

    # 2. Load Tokenizer & Model explicitly mapped globally
    logger.info("Loading Tokenizer and Base Model via native AutoClasses...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model_kwargs = {"device_map": "auto", "trust_remote_code": True}
    if bnb_config:
        model_kwargs["quantization_config"] = bnb_config

    model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

    # 3. Apply LoRA securely bypassing explicit limits
    logger.info("Injecting LoRA specific boundaries via get_peft_model...")
    model = get_peft_model(model, LORA_CONFIG)
    model.print_trainable_parameters()

    # 4. Train
    logger.info("Initializing SFTTrainer tracking evaluation bounds...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["test"],
        dataset_text_field="text",
        max_seq_length=1024,
        tokenizer=tokenizer,
        args=TRAINING_ARGS
    )

    logger.info("Starting Fine-tuning Sequence mapped autonomously...")
    train_result = trainer.train()

    logger.info("Training Complete! Evaluating models natively against split distributions...")
    metrics = trainer.evaluate()
    logger.info(f"Final Eval Metrics: {metrics}")

    # Save adapter cleanly globally
    logger.info(f"Saving LoRA adapter boundaries locally mapped to {OUTPUT_DIR}")
    trainer.save_model(OUTPUT_DIR)

def merge_and_save_full_model():
    has_gpu = torch.cuda.is_available()
    model_name = MODEL_NAME if has_gpu else "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

    logger.info("Reloading unquantized Base Model explicitly for global merging processes...")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto" if has_gpu else "cpu",
        torch_dtype=torch.float16 if has_gpu else torch.float32,
        trust_remote_code=True
    )

    from peft import PeftModel
    logger.info("Attaching LoRA Adapter explicitly targeting the local base mapping...")
    model = PeftModel.from_pretrained(base_model, OUTPUT_DIR)

    logger.info("Merging LoRA weights actively onto Base tensors mapping natively...")
    merged_model = model.merge_and_unload()

    merged_dir = os.path.join(OUTPUT_DIR, "merged")
    logger.info(f"Saving fully integrated merged models dynamically targeting {merged_dir}")
    merged_model.save_pretrained(merged_dir)

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.save_pretrained(merged_dir)

    logger.info("Merge sequence actively completed natively tracking OS directories!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA Fine-tuning execution explicitly bound.")
    parser.add_argument("--dry-run", action="store_true", help="Validate formats mapped dynamically.")
    parser.add_argument("--merge", action="store_true", help="Merge LoRA explicitly skipping mapping training.")
    args = parser.parse_args()

    if args.merge:
        merge_and_save_full_model()
    else:
        run_finetuning(dry_run=args.dry_run)
