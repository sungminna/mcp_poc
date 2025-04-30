from .extractor import InfoExtractor, KeywordExtractor
from .models import ExtractedInfoList, ExtractedKeywordList

class NoOpInfoExtractor(InfoExtractor):
    async def extract(self, user_message: str) -> ExtractedInfoList:
        """No-op extractor that returns an empty ExtractedInfoList."""
        return ExtractedInfoList(information=[])

class NoOpKeywordExtractor(KeywordExtractor):
    async def extract(self, user_message: str) -> ExtractedKeywordList:
        """No-op extractor that returns an empty ExtractedKeywordList."""
        return ExtractedKeywordList(keywords=[]) 