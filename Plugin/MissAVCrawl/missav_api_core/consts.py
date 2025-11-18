import re

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Referer": "https://www.missav.ws/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


regex_title = re.compile(r'<h1 class="text-base lg:text-lg text-nord6">(.*?)</h1>')
regex_video_code = re.compile(r'<span class="font-medium">(.*?)</span>')
regex_publish_date = re.compile(r'class="font-medium">(.*?)</time>')
regex_thumbnail = re.compile(r'og:image" content="(.*?)cover-n.jpg')
regex_m3u8_js = re.compile(r"'m3u8(.*?)video")