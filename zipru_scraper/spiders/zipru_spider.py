import scrapy

class ZipruSpider(scrapy.Spider):
    name = 'zipru'
    start_urls = ['http://zipru.to/torrents.php?category=1;18;41;49']

     def parse(self, response):
        # proceed to other pages of the listings
        for page_url in response.css('a[title ~= page]::attr(href)').extract():
            page_url = response.urljoin(page_url)
            yield scrapy.Request(url=page_url, callback=self.parse)
