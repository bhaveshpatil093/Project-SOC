import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logger = logging.getLogger(__name__)

SOC_SYSTEM_PROMPT = """You are an expert cybersecurity analyst assistant for the ISRO ISTRAC SOC team.
You help Level-1 SOC engineers investigate security alerts.
You have access to alert details, SHAP feature importance, MITRE ATT&CK context,
and historical alert data. Always be precise, concise, and actionable.
Format responses as: Summary → Evidence → Recommended Action.
Never make up data — only use what is provided in context."""

class SLMEngine:
    def __init__(self, 
                 model_name: str = "microsoft/Phi-3-mini-4k-instruct",
                 device: str = "cpu",
                 max_new_tokens: int = 512,
                 load_in_4bit: bool = False):
        self.model_name = model_name
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.load_in_4bit = load_in_4bit
        
        self.tokenizer = None
        self.model = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    async def load(self):
        logger.info(f"Loading SLM {self.model_name}...")
        
        # GPU / MPS / CPU resolution
        if self.device == "cpu":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"

        device_map = "auto" if self.device != "cpu" else None
        
        kwargs = {}
        if self.load_in_4bit:
            kwargs["load_in_4bit"] = True
            
        try:
            # Run in executor to prevent blocking FastAPI async event loop
            def _load():
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name, 
                    device_map=device_map,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    trust_remote_code=True,
                    **kwargs
                )
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _load)
            
            logger.info(f"SLM loaded securely on {self.device}")
            return {"status": "loaded", "model": self.model_name, "device": self.device}
            
        except Exception as e:
            logger.error(f"Failed to load primary SLM: {e}")
            logger.info("Initiating fallback to TinyLlama/TinyLlama-1.1B-Chat-v1.0")
            self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            def _load_fallback():
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map=device_map,
                    torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
                    **kwargs
                )
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _load_fallback)
            return {"status": "loaded_fallback", "model": self.model_name, "device": self.device}

    def generate(self, prompt: str, system_prompt: str = None,
                 temperature: float = 0.3, max_new_tokens: int = None) -> str:
        if not self.is_loaded():
            raise RuntimeError("Model is not loaded into memory")
            
        sys_p = system_prompt or SOC_SYSTEM_PROMPT
        max_tokens = max_new_tokens or self.max_new_tokens
        
        messages = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": prompt}
        ]
        
        # Format explicitly via the model's chat template ensuring correct delimiter tokens
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
            
        # Decode and strip prompt natively
        input_length = inputs.input_ids.shape[1]
        generated_tokens = outputs[0][input_length:]
        response = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        return response.strip()

    async def generate_async(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        loop = asyncio.get_event_loop()
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
_slm_engine = SLMEngine()

def get_slm_engine() -> SLMEngine:
    return _slm_engine
