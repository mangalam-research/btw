from lib.settings import s

s.LEXICOGRAPHY_LOCK_EXPIRY = 48  # Locks expire after 48 hours

# The number of seconds to throttle starting a preparation task when
# get_cached_value is called on a Chunk.
s.LEXICOGRAPHY_THROTTLING = 30

# The timeout of the XML data in the article_display cache, in seconds.
s.LEXICOGRAPHY_XML_TIMEOUT = 30 * 60
