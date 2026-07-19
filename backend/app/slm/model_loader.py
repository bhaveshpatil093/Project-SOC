import asyncio
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.logging_config import get_logger
logger = get_logger(__name__)

SOC_SYSTEM_PROMPT = """You are an expert cybersecurity analyst assistant for the ISRO ISTRAC SOC team.
You help Level-1 SOC engineers investigate security alerts.
You have access to alert details, SHAP feature importance, MITRE ATT&CK context,
and historical alert data. Always be precise, concise, and actionable.
Format responses as: Summary → Evidence → Recommended Action.
Never make up data — only use what is provided in context."""

class SLMEngine:
    def __init__(self,
                 model_name: str = "auto",
                 device: str = "cpu",
                 max_new_tokens: int = 512,
                 load_in_4bit: bool = False):
        self.model_name = model_name
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.load_in_4bit = load_in_4bit

        self.tokenizer = None
        self.model = None
        self.is_finetuned = False
        self.finetuned_path = None
        self.load_time_seconds = 0.0
        self.estimated_memory_mb = 0.0

        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()        # used only in generate() (sync)
        self._load_lock = asyncio.Lock()     # used in load() / reload() (async)

    def _resolve_model_path(self, target_model: str):
        finetuned_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/saved/phi3-soc-finetuned/merged"))

        if target_model == "auto":
            if os.path.exists(finetuned_dir):
                return finetuned_dir, True
            return "microsoft/Phi-3-mini-4k-instruct", False
        if target_model == "finetuned":
            if os.path.exists(finetuned_dir):
                return finetuned_dir, True
            logger.warning(f"Finetuned model not found at {finetuned_dir}. Falling back to base.")
            return "microsoft/Phi-3-mini-4k-instruct", False
        if target_model == "base":
            return "microsoft/Phi-3-mini-4k-instruct", False
        return target_model, False

    async def load(self):
        async with self._load_lock:
            start_t = time.time()

            resolved_path, is_ft = self._resolve_model_path(self.model_name)
            logger.info(f"Loading SLM. Target: {self.model_name}, Resolved: {resolved_path}, Finetuned: {is_ft}")

            self.finetuned_path = resolved_path if is_ft else None
            self.is_finetuned = is_ft

            if self.device == "cpu":
                if torch.cuda.is_available():
                    self.device = "cuda"
                elif torch.backends.mps.is_available():
                    # Disabled mps auto-selection due to Metal crashes (IOGPUMetalCommandBuffer)
                    self.device = "cpu"

            device_map = "auto" if self.device != "cpu" else None

            kwargs = {}
            if self.load_in_4bit:
                kwargs["load_in_4bit"] = True

            loop = asyncio.get_running_loop()

            try:
                def _load():
                    from transformers import AutoConfig
                    config = AutoConfig.from_pretrained(resolved_path, trust_remote_code=True)
                    if getattr(config, "rope_scaling", None):
                        config.rope_scaling = None

                    tokenizer = AutoTokenizer.from_pretrained(resolved_path, trust_remote_code=True)
                    model = AutoModelForCausalLM.from_pretrained(
                        resolved_path,
                        config=config,
                        device_map=device_map,
                        torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                        trust_remote_code=True,
                        **kwargs
                    )
                    return tokenizer, model

                self.tokenizer, self.model = await loop.run_in_executor(self._executor, _load)
                self.model_name = resolved_path if is_ft else "microsoft/Phi-3-mini-4k-instruct"

            except Exception as e:
                import traceback
                logger.error(f"Failed to load primary SLM: {e}")
                traceback.print_exc()
                logger.info("Initiating fallback to TinyLlama/TinyLlama-1.1B-Chat-v1.0")
                self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
                self.is_finetuned = False
                self.finetuned_path = None
                try:
                    def _load_fallback():
                        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                        model = AutoModelForCausalLM.from_pretrained(
                            self.model_name,
                            device_map=device_map,
                            torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                            **kwargs
                        )
                        return tokenizer, model
                    self.tokenizer, self.model = await loop.run_in_executor(self._executor, _load_fallback)
                except Exception as e2:
                    logger.error(f"Fallback SLM load also failed: {e2}")
                    return self.get_model_info()

            self.load_time_seconds = time.time() - start_t

            if self.device == "cuda" and torch.cuda.is_available():
                self.estimated_memory_mb = torch.cuda.memory_allocated() / (1024*1024)
            else:
                self.estimated_memory_mb = 3800.0

            logger.info(f"SLM loaded successfully on {self.device} in {self.load_time_seconds:.2f}s. is_loaded={self.is_loaded()}")
            return self.get_model_info()

    def get_model_info(self) -> dict:
        return {
            "model_name": self.model_name,
            "is_finetuned": self.is_finetuned,
            "finetuned_path": self.finetuned_path,
            "device": self.device,
            "loaded": self.is_loaded(),
            "load_time_seconds": self.load_time_seconds,
            "estimated_memory_mb": self.estimated_memory_mb
        }

    async def reload(self, model_name: str = "auto"):
        logger.info(f"Hot-reloading SLM to target: {model_name}")
        self.unload()
        self.model_name = model_name
        return await self.load()

    def generate(self, prompt: str, system_prompt: str = None,
                 temperature: float = 0.3, max_new_tokens: int = None) -> str:
        with self._lock:
            if not self.is_loaded():
                raise RuntimeError("Model is not loaded into memory")

            sys_p = system_prompt or SOC_SYSTEM_PROMPT
            max_tokens = max_new_tokens or self.max_new_tokens

            messages = [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": prompt}
            ]

            text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True if temperature > 0 else False,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            input_length = inputs.input_ids.shape[1]
            generated_tokens = outputs[0][input_length:]
            response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
            return response.strip()

    async def generate_async(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, lambda: self.generate(prompt, system_prompt, **kwargs))

    def is_loaded(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def unload(self):
        if self.model:
            del self.model
            self.model = None
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif torch.backends.mps.is_available():
            torch.mps.empty_cache()

# Global Instance binding
_slm_engine = SLMEngine(model_name="auto")

def get_slm_engine() -> SLMEngine:
    return _slm_engine
