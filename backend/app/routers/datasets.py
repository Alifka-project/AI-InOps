"""Dataset endpoints: parse uploaded CSVs, load the sample, fetch templates."""

from __future__ import annotations

import io
from typing import Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

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


MAX_COMBINED_BYTES = 15 * 1024 * 1024  # 15 MB for a combined workbook/zip


@router.post("/parse-combined", response_model=ValidationResponse)
async def parse_combined(
    name: str = Form("Uploaded dataset"),
    file: UploadFile = File(...),
) -> ValidationResponse:
    """Parse a single combined file holding all inputs.

    Accepts an Excel workbook (.xlsx — one sheet per input), a ZIP of CSVs
    (one file per input), or a canonical dataset JSON (a previous export).
    """
    raw = await file.read()
    if len(raw) > MAX_COMBINED_BYTES:
        raise HTTPException(
            status_code=413, detail=f"{file.filename}: file exceeds 15 MB limit."
        )
    fname = (file.filename or "").lower()

    try:
        if fname.endswith((".xlsx", ".xlsm", ".xls")):
            ds = dsmod.build_from_excel(raw, name=name, is_sample=False)
        elif fname.endswith(".zip"):
            ds = dsmod.build_from_zip(raw, name=name, is_sample=False)
        elif fname.endswith(".json"):
            import json

            try:
                payload = json.loads(raw.decode("utf-8-sig"))
            except Exception as exc:  # noqa: BLE001
                return ValidationResponse(ok=False, errors=[f"Invalid JSON: {exc}"])
            model = Dataset(**payload)  # pydantic validates the canonical shape
            return ValidationResponse(
                ok=True, dataset=model, warnings=model.meta.warnings
            )
        else:
            # Try Excel first, then ZIP, as a best-effort fallback on odd names.
            try:
                ds = dsmod.build_from_excel(raw, name=name, is_sample=False)
            except dsmod.DatasetError:
                ds = dsmod.build_from_zip(raw, name=name, is_sample=False)
    except dsmod.DatasetError as exc:
        return ValidationResponse(ok=False, errors=[str(exc)])
    except Exception as exc:  # noqa: BLE001
        return ValidationResponse(
            ok=False, errors=[f"Could not read {file.filename!r}: {exc}"]
        )

    return ValidationResponse(
        ok=True, dataset=Dataset(**ds), warnings=ds["meta"]["warnings"]
    )


@router.get("/sample", response_model=Dataset)
def sample_dataset() -> Dataset:
    """The clearly-labelled synthetic SAMPLE dataset (for demo/testing only)."""
    return Dataset(**dg.sample_dataset())


@router.get("/template-combined")
def template_combined(format: str = "xlsx") -> StreamingResponse:
    """Download a single combined template pre-filled with the sample data:
    an Excel workbook (default) or a ZIP of CSVs."""
    if format == "zip":
        data = dg.sample_zip_bytes()
        media = "application/zip"
        filename = "digital-twin-template.zip"
    else:
        data = dg.sample_excel_bytes()
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "digital-twin-template.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
