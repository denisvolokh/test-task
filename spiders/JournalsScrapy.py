__author__ = 'barmalei4ik'

import scrapy
from scrapy.crawler import CrawlerProcess

class JournalsScrapy(scrapy.Spider):
    name = "journals"
    start_urls = ["https://cos.io/top/"]

    def parse(self, response):
        path = '//*[@id="journals"]/div[1]/div[2]/div[2]/table/tbody/tr[1]'

        sel = scrapy.Selector(response)
        for item in sel.xpath(path):
            print item


if __name__ == "__main__":

    crawler = CrawlerProcess(JournalsScrapy())
    crawler.start()
