"""Notebook-compatible assessment with explicit errors and identity-safe checkpoints."""
from pathlib import Path
import hashlib
import json
import os
import time
from typing import Any, Callable, Optional

import pandas as pd
from filelock import FileLock
def OpenAI(*args, **kwargs):
    """Load the SDK only when constructing a real client (offline tests need none)."""
    from openai import OpenAI as Client
    return Client(*args, **kwargs)
from tqdm import tqdm


class AssessmentError(RuntimeError):
    """A provider failure or refusal; never a negative scientific assessment."""


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()


def _atomic(path, content):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class LLM_wrapper:
    def __init__(self, model_name: str, system_prompt: str,
                 output_format_class: Any, client=None) -> None:
        self.client = client if client is not None else OpenAI(timeout=60, max_retries=0)
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.output_format_class = output_format_class

    def generate_nan_output(self) -> Any:
        """Legacy helper for nullable schemas only; never used on API failure."""
        return self.output_format_class(
            **{field: None for field in self.output_format_class.model_fields}
        )

    def assess_one_row(self, user_prompt: str, max_retries: int = 3) -> Any:
        """Return validated output, or raise a redacted AssessmentError."""
        if max_retries < 1 or max_retries > 10:
            raise ValueError("max_retries must be between 1 and 10")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("Assessment requires nonempty text")
        for attempt in range(max_retries):
            try:
                response = self.client.responses.parse(
                    model=self.model_name,
                    input=[{"role": "system", "content": self.system_prompt},
                           {"role": "user", "content": user_prompt}],
                    text_format=self.output_format_class,
                    truncation="auto",
                )
                result = response.output_parsed
                if result is None:
                    raise AssessmentError("Provider returned no structured assessment")
                return self.output_format_class.model_validate(result)
            except Exception:
                if attempt + 1 < max_retries:
                    time.sleep(0.6 * (attempt + 1))
        raise AssessmentError(f"Assessment failed after {max_retries} attempts") from None

    @staticmethod
    def load_input_file(input_file_path: str, text_column: str,
                        debug_mode: bool) -> pd.DataFrame:
        path = str(input_file_path)
        if path.endswith(".csv"):
            df = pd.read_csv(path, nrows=10 if debug_mode else None)
        elif path.endswith((".parquet", ".parquet.br")):
            df = pd.read_parquet(path)
        else:
            raise ValueError("Supported input types: CSV and Parquet")
        if text_column not in df.columns:
            raise ValueError(f"Missing required column '{text_column}' in the input file")
        return df.head(10).copy() if debug_mode else df

    def assess_dataframe(
        self, input_file_path: str, text_column: str, output_dir: str,
        save_ckpt_every: int = 10, debug_mode: bool = False,
        row_filter: Optional[Callable[[pd.Series], bool]] = None,
        stop_requested: Optional[Callable[[], bool]] = None,
    ) -> pd.DataFrame:
        """Assess unchanged notebook inputs; JSON checkpoints are authoritative.

        Legacy model-only CSV checkpoints are intentionally ignored. Input columns
        colliding with generated fields are preserved under input__ names.
        """
        if save_ckpt_every < 1:
            raise ValueError("save_ckpt_every must be positive")
        df = self.load_input_file(input_file_path, text_column, debug_mode)
        selected = [int(i) for i, row in df.iterrows()
                    if row_filter is None or bool(row_filter(row))]
        identity = {
            "version": 2,
            "input": hashlib.sha256(Path(input_file_path).read_bytes()).hexdigest(),
            "model": self.model_name, "prompt": _digest(self.system_prompt),
            "schema": _digest(self.output_format_class.model_json_schema()),
            "code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "text_column": text_column, "selected_rows": selected,
            "debug": debug_mode, "truncation": "auto",
        }
        run_id = _digest(identity)
        directory = Path(output_dir) / "checkpoints"
        directory.mkdir(parents=True, exist_ok=True)
        checkpoint = directory / f"{run_id}.checkpoint.json"
        results = {}
        with FileLock(str(checkpoint) + ".lock", timeout=0):
            if checkpoint.exists():
                saved = json.loads(checkpoint.read_text())
                if saved.get("identity") != identity:
                    raise ValueError("Incompatible checkpoint")
                results = saved["results"]
            for i in tqdm(selected):
                previous = results.get(str(i), {})
                if previous.get("status") == "succeeded":
                    self.output_format_class.model_validate(previous["assessment"])
                    continue
                if stop_requested and stop_requested():
                    break
                value = df.at[i, text_column]
                if not isinstance(value, str) or not value.strip():
                    results[str(i)] = {"status": "missing", "assessment": None}
                else:
                    try:
                        assessment = self.assess_one_row(value)
                        results[str(i)] = {"status": "succeeded",
                                           "assessment": assessment.model_dump(mode="json")}
                    except Exception:
                        results[str(i)] = {"status": "failed", "assessment": None,
                                           "error": "Assessment failed"}
                # Every completed row is durable; save_ckpt_every retained for API compatibility.
                _atomic(checkpoint, json.dumps({"identity": identity, "results": results}))
            fields = list(self.output_format_class.model_fields)
            reserved = fields + ["generation", "assessment_status", "assessment_error", "run_id"]
            for name in reserved:
                if name in df.columns:
                    if f"input__{name}" in df.columns:
                        raise ValueError(f"Reserved input column collision: {name}")
                    df = df.rename(columns={name: f"input__{name}"})
                df[name] = pd.Series([None] * len(df), index=df.index, dtype=object)
            for i in df.index:
                outcome = results.get(str(i), {"status": "pending" if i in selected else "not_selected"})
                df.at[i, "assessment_status"] = outcome["status"]
                df.at[i, "assessment_error"] = outcome.get("error")
                df.at[i, "run_id"] = run_id
                if outcome["status"] == "succeeded":
                    df.at[i, "generation"] = True
                    for name, value in outcome["assessment"].items():
                        df.at[i, name] = value
            _atomic(checkpoint, json.dumps({"identity": identity, "results": results}))
            _atomic(directory / f"{run_id}.checkpoint.csv", df.to_csv(index=False))
        return df
