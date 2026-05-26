"""CSS selectors for parsing Google Scholar Labs result HTML.

Centralized here so they can be updated in one place when Google changes markup.
"""

TITLE = "h3.gs_rt a, h3 a"
AUTHORS = "div.gs_a"
ABSTRACT = "div.gs_rs"
CITATION_LINK = "div.gs_fl a[href*='cites=']"
ROOT = "[data-aid]"
PDF_LINK = "div.gs_ggsd a[href$='.pdf']"
