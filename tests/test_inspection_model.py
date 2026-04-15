from __future__ import annotations

from typing import get_type_hints

from playtrace.models.inspection import InspectionDetail
from playtrace.render.source_views import render_inspection
from playtrace.services.inspector import InspectorService


def test_inspection_detail_type_is_shared_between_service_and_render_layers() -> None:
    assert get_type_hints(render_inspection)["detail"] is InspectionDetail
    assert get_type_hints(InspectorService.load)["return"] is InspectionDetail
