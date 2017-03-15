import scrapy

class ZipruSpider(scrapy.Spider):
    name = 'zipru'
    start_urls = ['http://zipru.to/torrents.php?category=1;18;41;49']

     def parse(self, response):
        # proceed to other pages of the listings
        for page_url in response.css('a[title ~= page]::attr(href)').extract():
            page_url = response.urljoin(page_url)
            yield scrapy.Request(url=page_url, callback=self.parse)

        # extract the torrent items
        for tr in response.css('table.lista2t tr.lista2'):
            tds = tr.css('td')
            link = tds[1].css('a')[0]
            yield {
                'title' : link.css('::attr(title)').extract_first(),
                'url' : response.urljoin(link.css('::attr(href)').extract_first()),
                'date' : tds[2].css('::text').extract_first(),
                'size' : tds[3].css('::text').extract_first(),
                'seeders': int(tds[4].css('::text').extract_first()),
                'leechers': int(tds[5].css('::text').extract_first()),
                'uploader': tds[7].css('::text').extract_first(),
            }
