from playtrace.models.enums import SourceName


class BamCollector:
    name = SourceName.BAM.value

    def is_available(self) -> bool:
        return False
