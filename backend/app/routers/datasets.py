"""Dataset endpoints: parse uploaded CSVs, load the sample, fetch templates."""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core import data_generator as dg
from core import dataset as dsmod

from ..models import Dataset, ValidationResponse

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file


async def _read(file: Optional[UploadFile]) -> Optional[str]:
    if file is None:
        return None
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=413, detail=f"{file.filename}: file exceeds 5 MB limit."
        )
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail=f"{file.filename}: file is not valid UTF-8 text."
        )


@router.post("/parse", response_model=ValidationResponse)
async def parse_upload(
    name: str = Form("Uploaded dataset"),
    sales: UploadFile = File(...),
    suppliers: UploadFile = File(...),
    transport_costs: UploadFile = File(...),
    external: UploadFile = File(...),
    inventory: UploadFile = File(...),
    orders: UploadFile = File(...),
    warehouse_params: UploadFile = File(...),
    transport_history: UploadFile = File(...),
    materials: Optional[UploadFile] = File(None),
) -> ValidationResponse:
    """Parse and validate uploaded CSVs into the canonical dataset.

    All eight required inputs must be provided; ``materials`` is optional
    reference data. Returns structured errors instead of a 500 on bad input.
    """
    files = {
        "sales": sales,
        "suppliers": suppliers,
        "transport_costs": transport_costs,
        "external": external,
        "inventory": inventory,
        "orders": orders,
        "warehouse_params": warehouse_params,
        "transport_history": transport_history,
        "materials": materials,
    }
    texts: Dict[str, str] = {}
    for kind, f in files.items():
        content = await _read(f)
        if content is not None:
            texts[kind] = content

    try:
        ds = dsmod.build_from_csv_texts(texts, name=name, is_sample=False)
    except dsmod.DatasetError as exc:
        return ValidationResponse(ok=False, errors=[str(exc)])

    return ValidationResponse(
        ok=True, dataset=Dataset(**ds), warnings=ds["meta"]["warnings"]
    )


@router.get("/sample", response_model=Dataset)
def sample_dataset() -> Dataset:
    """The clearly-labelled synthetic SAMPLE dataset (for demo/testing only)."""
    return Dataset(**dg.sample_dataset())


@router.get("/templates/{kind}")
def template(kind: str) -> dict:
    """Return a CSV template (headers + a couple of sample rows) for one input."""
    if kind not in dsmod.SCHEMAS:
        raise HTTPException(status_code=404, detail=f"Unknown input type {kind!r}.")
    texts = dg.sample_csv_texts()
    if kind not in texts:
        raise HTTPException(status_code=404, detail=f"No template for {kind!r}.")
    # First few rows only, to keep the template small.
    lines = texts[kind].splitlines()
    preview = "\n".join(lines[: min(len(lines), 6)])
    return {
        "kind": kind,
        "filename": f"{kind}.csv",
        "csv": preview,
        "columns": list(dsmod.SCHEMAS[kind].keys()),
    }
