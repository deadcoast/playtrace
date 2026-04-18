from playtrace.models.enums import SourceName


class SrumCollector:
    name = SourceName.SRUM.value

    def is_available(self) -> bool:
        return False
