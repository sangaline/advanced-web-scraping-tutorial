import os, tempfile, time, sys, logging
logger = logging.getLogger(__name__)

import dryscrape
import pytesseract
from PIL import Image

from scrapy.downloadermiddlewares.redirect import RedirectMiddleware

class ThreatDefenceRedirectMiddleware(RedirectMiddleware):
    def _redirect(self, redirected, request, spider, reason):
        # act normally if this isn't a threat defense redirect
        if not self.is_threat_defense_url(redirected.url):
            return super()._redirect(redirected, request, spider, reason)

        logger.debug(f'Zipru threat defense triggered for {request.url}')
        request.cookies = self.bypass_threat_defense(redirected.url)
        request.dont_filter = True # prevents the original link being marked a dupe
        return request

    def is_threat_defense_url(self, url):
        return '://zipru.to/threat_defence.php' in url
