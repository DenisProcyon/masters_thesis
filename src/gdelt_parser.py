from gdeltdoc import GdeltDoc, Filters, near, repeat

f = Filters(
    start_date = "2020-01-01",
    end_date = "2022-12-01",
    keyword = "pobreza",
    country = ["MX", "ES"],
)

gd = GdeltDoc()

# Search for articles matching the filters
articles = gd.article_search(f)

# Get a timeline of the number of articles matching the filters
timeline = gd.timeline_search("timelinevol", f)

pass