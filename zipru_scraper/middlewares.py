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
        for key, value in settings['DEFAULT_REQUEST_HEADERS'].items():
            # seems to be a bug with how webkit-server handles accept-encoding
            if key.lower() != 'accept-encoding':
                self.dryscrape_session.set_header(key, value)

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

    def solve_captcha(self, img, width=1280, height=800):
        # take a screenshot of the page
        self.dryscrape_session.set_viewport_size(width, height)
        filename = tempfile.mktemp('.png')
        self.dryscrape_session.render(filename, width, height)

        # inject javascript to find the bounds of the captcha
        js = 'document.querySelector("img[src *= captcha]").getBoundingClientRect()'
        rect = self.dryscrape_session.eval_script(js)
        box = (int(rect['left']), int(rect['top']), int(rect['right']), int(rect['bottom']))

        # solve the captcha in the screenshot
        image = Image.open(filename)
        os.unlink(filename)
        captcha_image = image.crop(box)
        captcha = pytesseract.image_to_string(captcha_image)
        logger.debug(f'Solved the Zipru captcha: "{captcha}"')

        # submit the captcha
        input = self.dryscrape_session.xpath('//input[@id = "solve_string"]')[0]
        input.set(captcha)
        button = self.dryscrape_session.xpath('//button[@id = "button_submit"]')[0]
        url = self.dryscrape_session.url()
        button.click()

        # try again if it we redirect to a threat defense URL
        if self.is_threat_defense_url(self.wait_for_redirect(url)):
            return self.bypass_threat_defense()

        # otherwise return the cookies as a dict
        cookies = {}
        for cookie_string in self.dryscrape_session.cookies():
            if 'domain=zipru.to' in cookie_string:
                key, value = cookie_string.split(';')[0].split('=')
                cookies[key] = value
        return cookies
