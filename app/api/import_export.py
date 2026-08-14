"""`/import`, `/export` — stage 4: CSV/Excel and vCard contact interchange.

Full-graph backups (JSON+CSV, for the `make backup` cron job) are a
separate concern — see `app.services.backup_export`, run standalone rather
than through the API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile

from app.api.deps import get_import_export_handler
from app.handlers.import_export_handler import ImportExportHandler
from app.models.import_result import ImportSummary

router = APIRouter(tags=["import-export"])


@router.post("/import/csv", response_model=ImportSummary)
async def import_csv(
    file: UploadFile = File(...),
    handler: ImportExportHandler = Depends(get_import_export_handler),
) -> ImportSummary:
    data = await file.read()
    return await handler.import_csv(file.filename or "import.csv", data)


@router.post("/import/vcard", response_model=ImportSummary)
async def import_vcard(
    file: UploadFile = File(...),
    handler: ImportExportHandler = Depends(get_import_export_handler),
) -> ImportSummary:
    data = await file.read()
    return await handler.import_vcard(data)


@router.get("/export/csv")
async def export_csv(
    include_archived: bool = Query(default=False),
    handler: ImportExportHandler = Depends(get_import_export_handler),
) -> Response:
    data = await handler.export_csv(include_archived=include_archived)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts.csv"},
    )


@router.get("/export/vcard")
async def export_vcard(
    include_archived: bool = Query(default=False),
    handler: ImportExportHandler = Depends(get_import_export_handler),
) -> Response:
    data = await handler.export_vcard(include_archived=include_archived)
    return Response(
        content=data,
        media_type="text/vcard",
        headers={"Content-Disposition": "attachment; filename=contacts.vcf"},
    )
