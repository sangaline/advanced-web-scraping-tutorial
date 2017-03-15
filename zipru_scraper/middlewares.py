import os, tempfile, time, sys, logging
logger = logging.getLogger(__name__)

import dryscrape
import pytesseract
from PIL import Image

from scrapy.downloadermiddlewares.redirect import RedirectMiddleware

class ThreatDefenceRedirectMiddleware(RedirectMiddleware):
    def __init__(self, settings):
        super().__init__(settings)

        # start xvfb to support headless scraping
        if 'linux' in sys.platform:
            dryscrape.start_xvfb()

        self.dryscrape_session = dryscrape.Session(base_url='http://zipru.to')

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

    def bypass_threat_defense(self, url=None):
        # only navigate if any explicit url is provided
        if url:
            self.dryscrape_session.visit(url)

        # solve the captcha if there is one
        captcha_images = self.dryscrape_session.css('img[src *= captcha]')
        if len(captcha_images) > 0:
            return self.solve_captcha(captcha_images[0])

        # click on any explicit retry links
        retry_links = self.dryscrape_session.css('a[href *= threat_defence]')
        if len(retry_links) > 0:
            return self.bypass_threat_defense(retry_links[0].get_attr('href'))

        # otherwise, we're on a redirect page so wait for the redirect and try again
        self.wait_for_redirect()
        return self.bypass_threat_defense()

    def wait_for_redirect(self, url = None, wait = 0.1, timeout=10):
        url = url or self.dryscrape_session.url()
        for i in range(int(timeout//wait)):
            time.sleep(wait)
            if self.dryscrape_session.url() != url:
                return self.dryscrape_session.url()
        logger.error(f'Maybe {self.dryscrape_session.url()} isn\'t a redirect URL?')
        raise Exception('Timed out on the zipru redirect page.')
