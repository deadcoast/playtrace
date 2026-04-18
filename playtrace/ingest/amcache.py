from playtrace.models.enums import SourceName


class AmCacheCollector:
    name = SourceName.AMCACHE.value

    def is_available(self) -> bool:
        return False
