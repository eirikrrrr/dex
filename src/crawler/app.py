from crawler.utils.cleaners.asurascans import AsuraScan
from crawler.database.repository import CrawlerRepository
from crawler.database.sqlite import SQLiteDatabase


if __name__ == "__main__":
    db = SQLiteDatabase("data/crawler.db")
    db.initialize()
    
    crawler = AsuraScan("https://asurascans.com/")
    repository = CrawlerRepository(db)

    catalog = crawler.get_browse_catalog()