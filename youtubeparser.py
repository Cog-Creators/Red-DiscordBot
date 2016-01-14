from bs4 import BeautifulSoup
import requests
import aiohttp
import asyncio

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

async def parsePlaylist(url):
	try:
		page = await aiohttp.post(url, headers=headers)
		page = await page.text()

		#page = requests.get(url, headers=headers)
		soup = BeautifulSoup(page, 'html.parser')
		tags = soup.find_all("tr", class_="pl-video yt-uix-tile ")
		links = []

		for tag in tags:
			links.append("https://www.youtube.com/watch?v=" + tag['data-video-id'])
		if links != []:
			return links
		else:
			return False
	except:
		return False

async def getTitle(url):
	try:
		page = requests.get(url, headers=headers)
		soup = BeautifulSoup(page.content, 'html.parser')
		return soup.title.string.replace(" - YouTube", "")
	except:
		return False