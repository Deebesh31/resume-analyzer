"""Local resume entity extraction using a pinned, quantized ONNX model.

The model follows the standard token-classification / BIO-tagging approach used
in resume parsing research. Model files are fetched lazily and cached by the
Hugging Face Hub client; resume text is not sent to Hugging Face for inference.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass


MODEL_ID = os.getenv("RESUME_NER_MODEL_ID", "oksomu/resume-ner")
MODEL_REVISION = os.getenv(
    "RESUME_NER_MODEL_REVISION",
    "4d0a4e95743080b920072f1d481d946f5628bee6",
)
MAX_TEXT_CHARACTERS = 120_000
MAX_MODEL_TOKENS = 20_000
MODEL_CONTEXT_TOKENS = 510
WINDOW_OVERLAP_TOKENS = 64


class ResumeParserUnavailable(RuntimeError):
    """Raised when the optional local NER model cannot be loaded or run."""


@dataclass
class _ResumeModel:
    tokenizer: object
    session: object
    labels: dict[int, str]
    cls_token_id: int
    sep_token_id: int
    input_names: set[str]


_model_lock = threading.Lock()
_model_instance: _ResumeModel | None = None
_model_error: str | None = None


def _load_model() -> _ResumeModel:
    global _model_instance, _model_error
    if _model_instance is not None:
        return _model_instance
    if _model_error:
        raise ResumeParserUnavailable(_model_error)

    with _model_lock:
        if _model_instance is not None:
            return _model_instance
        if _model_error:
            raise ResumeParserUnavailable(_model_error)
        try:
            import onnxruntime as ort
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer

            revision = MODEL_REVISION
            config_path = hf_hub_download(MODEL_ID, "config.json", revision=revision)
            tokenizer_path = hf_hub_download(MODEL_ID, "tokenizer.json", revision=revision)
            model_path = hf_hub_download(
                MODEL_ID,
                "onnx/model_quantized.onnx",
                revision=revision,
            )

            with open(config_path, encoding="utf-8") as config_file:
                config = json.load(config_file)
            labels = {
                int(index): label
                for index, label in config.get("id2label", {}).items()
            }
            if not labels:
                raise ValueError("The resume model does not provide an id2label map.")

            tokenizer = Tokenizer.from_file(tokenizer_path)
            cls_token_id = tokenizer.token_to_id("[CLS]")
            sep_token_id = tokenizer.token_to_id("[SEP]")
            if cls_token_id is None or sep_token_id is None:
                raise ValueError("The resume model tokenizer is missing BERT boundary tokens.")

            session_options = ort.SessionOptions()
            session_options.intra_op_num_threads = 1
            session_options.inter_op_num_threads = 1
            session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=["CPUExecutionProvider"],
            )
            _model_instance = _ResumeModel(
                tokenizer=tokenizer,
                session=session,
                labels=labels,
                cls_token_id=cls_token_id,
                sep_token_id=sep_token_id,
                input_names={item.name for item in session.get_inputs()},
            )
            return _model_instance
        except Exception:
            _model_error = (
                "The local resume entity model could not be loaded. "
                "Check the service's model download access and available memory."
            )
            raise ResumeParserUnavailable(_model_error) from None


def _model_inputs(model: _ResumeModel, token_ids: list[int]):
    import numpy as np

    input_values = {
        "input_ids": np.asarray([token_ids], dtype=np.int64),
        "attention_mask": np.ones((1, len(token_ids)), dtype=np.int64),
        "token_type_ids": np.zeros((1, len(token_ids)), dtype=np.int64),
        "position_ids": np.arange(len(token_ids), dtype=np.int64)[None, :],
    }
    return {
        name: value
        for name, value in input_values.items()
        if name in model.input_names
    }


def _run_token_classifier(model: _ResumeModel, text: str) -> tuple[list[dict], bool]:
    import numpy as np

    truncated = len(text) > MAX_TEXT_CHARACTERS
    bounded_text = text[:MAX_TEXT_CHARACTERS]
    encoding = model.tokenizer.encode(bounded_text, add_special_tokens=False)
    token_ids = encoding.ids[:MAX_MODEL_TOKENS]
    offsets = encoding.offsets[:MAX_MODEL_TOKENS]
    truncated = truncated or len(encoding.ids) > MAX_MODEL_TOKENS
    if not token_ids:
        return [], truncated

    step = MODEL_CONTEXT_TOKENS - WINDOW_OVERLAP_TOKENS
    logits_sum = None
    logits_count = np.zeros(len(token_ids), dtype=np.float32)
    output_name = model.session.get_outputs()[0].name

    for start in range(0, len(token_ids), step):
        end = min(start + MODEL_CONTEXT_TOKENS, len(token_ids))
        window_ids = [model.cls_token_id, *token_ids[start:end], model.sep_token_id]
        outputs = model.session.run(
            [output_name],
            _model_inputs(model, window_ids),
        )
        window_logits = np.asarray(outputs[0], dtype=np.float32)[0, 1:-1, :]
        if logits_sum is None:
            logits_sum = np.zeros((len(token_ids), window_logits.shape[-1]), dtype=np.float32)
        logits_sum[start:end] += window_logits[: end - start]
        logits_count[start:end] += 1
        if end == len(token_ids):
            break

    mean_logits = logits_sum / np.maximum(logits_count[:, None], 1.0)
    shifted = mean_logits - mean_logits.max(axis=1, keepdims=True)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    label_ids = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)

    spans: list[dict] = []
    active_label = None
    active_start = 0
    active_end = 0
    active_scores: list[float] = []

    def emit():
        if active_label and active_end > active_start:
            value = bounded_text[active_start:active_end].strip()
            if value:
                spans.append({
                    "label": active_label,
                    "value": value,
                    "start": active_start,
                    "end": active_end,
                    "confidence": round(sum(active_scores) / len(active_scores), 4),
                })

    for index, (label_id, (start, end)) in enumerate(zip(label_ids, offsets)):
        if start == end:
            predicted_label = "O"
        else:
            predicted_label = model.labels.get(int(label_id), "O")
        if predicted_label == "O":
            emit()
            active_label = None
            active_scores = []
            continue

        if "-" in predicted_label:
            prefix, entity_label = predicted_label.split("-", 1)
        elif "_" in predicted_label:
            prefix, entity_label = predicted_label.split("_", 1)
        else:
            prefix, entity_label = "B", predicted_label
        entity_label = entity_label.upper()
        if prefix.upper() not in {"B", "I"}:
            emit()
            active_label = None
            active_scores = []
            continue

        starts_entity = prefix.upper() == "B" or entity_label != active_label
        if starts_entity:
            emit()
            active_label = entity_label
            active_start = start
            active_end = end
            active_scores = [float(confidence[index])]
        else:
            active_end = end
            active_scores.append(float(confidence[index]))
    emit()

    return _deduplicate_spans(spans), truncated


def _deduplicate_spans(spans: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for span in spans:
        key = (span["label"], " ".join(span["value"].lower().split()))
        if key not in seen:
            result.append(span)
            seen.add(key)
        if len(result) >= 1200:
            break
    return result


def extract_resume_entities(text: str) -> dict:
    """Return entity spans predicted by the local resume token classifier."""
    if not text or not text.strip():
        return {"entities": [], "truncated": False}
    model = _load_model()
    try:
        entities, truncated = _run_token_classifier(model, text)
    except Exception:
        raise ResumeParserUnavailable("The local resume entity model could not process this document.") from None
    return {"entities": entities, "truncated": truncated}
