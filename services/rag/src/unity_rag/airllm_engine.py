"""Módulo 4: AirLLM sob demanda, uma instância, chamado só pelo executor de um worker.

API confirmada no checkout local (airllm-main/air_llm 4.0.0): AutoModel.from_pretrained
com device, dtype, max_seq_len, layer_shards_saving_path, compression, prefetching e
delete_original; model.tokenizer; generate delega a transformers.

AirLLM usa trust_remote_code=True internamente: só checkpoints locais conhecidos.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from .config import GeneratorConfig
from .context_builder import HFTokenizer

logger = logging.getLogger("unity_rag")


class GeneratorUnavailable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class GenerationCancelled(Exception):
    pass


def missing_assets(model_path: Path) -> list[str]:
    """Checagem offline completa antes de construir o modelo (evita snapshot_download)."""
    missing = []
    if not (model_path / "config.json").exists():
        missing.append("config.json")
    has_tokenizer = (model_path / "tokenizer.json").exists() or (model_path / "tokenizer.model").exists() or (
        (model_path / "vocab.json").exists() and (model_path / "merges.txt").exists()
    )
    if not has_tokenizer:
        missing.append("tokenizer")
    index = model_path / "model.safetensors.index.json"
    if index.exists():
        try:
            shards = set(json.loads(index.read_text(encoding="utf-8"))["weight_map"].values())
        except (OSError, ValueError, KeyError):
            missing.append("model.safetensors.index.json legível")
            shards = set()
        missing.extend(sorted(s for s in shards if not (model_path / s).exists()))
    elif not (model_path / "model.safetensors").exists() and not (model_path / "pytorch_model.bin").exists():
        missing.append("pesos (model.safetensors)")
    return missing


def disable_per_layer_gc() -> None:
    """Em CPU, o _post_hook do AirLLM chama clean_memory() (gc.collect + cuda.empty_cache)
    depois de cada camada, a cada token. Os pesos já voltam para `meta` por refcount, então
    a coleta não libera nada útil. Medido neste PC com Qwen2.5-1.5B bf16: 5,7 → 1,0 s/token,
    com saída idêntica. Ajuste só neste processo; o checkout vendorizado não é alterado."""
    import airllm.airllm_base as base

    base.clean_memory = lambda: None


class AirLlmEngine:
    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.state = "not_configured" if not config.enabled or config.model_path is None else "unloaded"
        self.reason: str | None = None if self.state == "unloaded" else "Gerador desabilitado ou sem model_path."
        self._model = None
        self._tokenizer: HFTokenizer | None = None
        self._lock = threading.Lock()  # uma geração por vez, mesmo após timeout/cancelamento
        self.model_name = config.repo_id or (config.model_path.name if config.model_path else "")

    @property
    def shards_dir(self) -> Path | None:
        if self.config.shards_path is None or self.config.model_path is None:
            return None
        return self.config.shards_path / self.config.model_path.name

    def check(self) -> None:
        if self.state == "not_configured":
            raise GeneratorUnavailable("generator_not_configured", self.reason or "Gerador não configurado.")
        assert self.config.model_path is not None
        missing = missing_assets(self.config.model_path)
        if missing:
            self.state, self.reason = "error", f"model_assets_missing: {', '.join(missing)} em {self.config.model_path}"
            raise GeneratorUnavailable("model_assets_missing", self.reason)

    def tokenizer(self) -> HFTokenizer:
        """Tokenizer exato do checkpoint, sem carregar os pesos."""
        if self._tokenizer is None:
            self.check()
            from transformers import AutoTokenizer

            tok = AutoTokenizer.from_pretrained(str(self.config.model_path), local_files_only=True)
            self._tokenizer = HFTokenizer(tok, f"{self.model_name} tokenizer")
        return self._tokenizer

    def load(self) -> None:
        if self._model is not None:
            return
        self.check()
        self.state, self.reason = "loading", None
        try:
            import torch
            from airllm import AutoModel

            if not self.config.device.startswith("cuda"):
                disable_per_layer_gc()
            model = AutoModel.from_pretrained(
                str(self.config.model_path),
                device=self.config.device,
                dtype=getattr(torch, self.config.dtype),
                max_seq_len=self.config.max_seq_len,
                # O AirLLM grava sempre em <dir>/splitted_model: um diretório por checkpoint
                # evita reutilizar camadas de outro modelo.
                layer_shards_saving_path=str(self.shards_dir) if self.shards_dir else None,
                compression=self.config.compression or None,
                prefetching=self.config.prefetching,
                delete_original=False,
            )
        except Exception as exc:
            self.state, self.reason = "error", f"{type(exc).__name__}: {exc}"
            logger.exception("falha ao carregar o AirLLM")
            raise GeneratorUnavailable("model_load_failed", self.reason) from exc
        self._model = model
        self.state = "ready"

    def generate(self, prompt: str, *, max_new_tokens: int, cancel: threading.Event,
                 on_token: Callable[[int], None] | None = None) -> tuple[str, int]:
        """Chamado pelo worker único. Cancelamento é cooperativo, verificado a cada token."""
        with self._lock:
            self.load()
            import torch
            from transformers import StoppingCriteria, StoppingCriteriaList

            tokenizer = self._model.tokenizer
            encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
            input_ids = encoded["input_ids"].to(self._model.device)
            attention = encoded["attention_mask"].to(self._model.device)
            prompt_length = input_ids.shape[1]

            class Watch(StoppingCriteria):
                def __call__(self, ids, scores, **kwargs):  # type: ignore[override]
                    generated = ids.shape[1] - prompt_length
                    if on_token is not None:
                        on_token(generated)
                    return cancel.is_set()

            with torch.inference_mode():
                output = self._model.generate(
                    input_ids=input_ids, attention_mask=attention, max_new_tokens=max_new_tokens,
                    use_cache=True, do_sample=False, return_dict_in_generate=True,
                    stopping_criteria=StoppingCriteriaList([Watch()]),
                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                )
            if cancel.is_set():
                raise GenerationCancelled()
            sequences = output.sequences if hasattr(output, "sequences") else output
            generated = sequences[0, prompt_length:]
            return tokenizer.decode(generated, skip_special_tokens=True).strip(), int(generated.shape[0])


class FakeEngine:
    """Gerador falso para testes: devolve o contexto recebido, com latência controlada."""

    def __init__(self, delay: float = 0.0, tokenizer=None) -> None:
        self.state = "unloaded"
        self.reason = None
        self.model_name = "test/fake-generator"
        self.delay = delay
        self.calls = 0
        self.concurrent = 0
        self.max_concurrent = 0
        self._tok = tokenizer
        self._lock = threading.Lock()

    def check(self) -> None:
        return None

    def tokenizer(self):
        return self._tok

    def load(self) -> None:
        self.state = "ready"

    def generate(self, prompt: str, *, max_new_tokens: int, cancel: threading.Event, on_token=None) -> tuple[str, int]:
        with self._lock:
            self.concurrent += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent)
            try:
                self.load()
                self.calls += 1
                end = time.monotonic() + self.delay
                step = 0
                while time.monotonic() < end:
                    if cancel.is_set():
                        raise GenerationCancelled()
                    step += 1
                    if on_token:
                        on_token(step)
                    time.sleep(0.01)
                return f"Resposta de teste baseada em {prompt.count('[S')} fontes.", 8
            finally:
                self.concurrent -= 1
