# xbmc-nfo importer
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
#
import os, re, os.path, time, datetime

class xbmcnfo(Agent.Movies):
	name = 'XBMC .nfo Importer'
	primary_provider = True
	languages = [Locale.Language.English]
	
	def search(self, results, media, lang):
		Log("Searching")

		pageUrl = "http://localhost:32400/library/metadata/" + media.id
		xml = XML.ElementFromURL(pageUrl)
		#Log('xml = ' + XML.StringFromElement(xml))
		nfoXML = xml.xpath('//MediaContainer/Video/Media/Part')[0]
		path1 = String.Unquote(nfoXML.get('file'))
		nfoFile = self.getRelatedFile(path1, '.nfo')
		Log('Looking for Movie NFO file at ' + nfoFile)

		if not os.path.exists(nfoFile):
			Log("ERROR: Can't find .nfo file for " + path1)
		else:
			nfoText = Core.storage.load(nfoFile)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				# Title
				try: media.name = nfoXML.xpath("title")[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# IMDB id
				try: media.id = nfoXML.xpath('./id')[0].text
				except: pass
				# Year
				try: media.year = nfoXML.xpath('./year')[0].text
				except: pass

				Log('Movie title: ' + media.name)
				Log('Year: ' + str(media.year))
   
				name = media.name
				results.Append(MetadataSearchResult(id=media.id, name=name, year=media.year, lang=lang, score=100))
				for result in results:
					try: Log('scraped results: ' + result.name + ' | year = ' + str(result.year) + ' | id = ' + result.id + '| score = ' + str(result.score))
					except: pass
			else:
				Log("ERROR: No <tvshow> tag in " + nfoFile + ". Aborting!")

	def getRelatedFile(self, videoFile, fileExtension):
		videoFileExtension = videoFile.split(".")[-1]
		return videoFile.replace('.' + videoFileExtension, fileExtension)
		
	def update(self, metadata, media, lang):
		Log('Update called for Movie with id = ' + media.id)
		pageUrl = "http://localhost:32400/library/metadata/" + media.id + "/tree"
		page = HTTP.Request(pageUrl)
		xml = XML.ElementFromURL(pageUrl)
		#Log('xml = ' + XML.StringFromElement(xml))
		nfoXML = xml.xpath('//MediaPart')[0]
		path1 = String.Unquote(nfoXML.get('file'))

		posterFilename = self.getRelatedFile(path1, '.tbn')
		if os.path.exists(posterFilename):
			posterData = Core.storage.load(posterFilename)
			metadata.posters[posterFilename] = Proxy.Media(posterData)
			Log('Found poster image at ' + posterFilename)

		fanartFilename = self.getRelatedFile(path1, '-fanart.jpg')
		if os.path.exists(fanartFilename):
			fanartData = Core.storage.load(fanartFilename)
			metadata.art[fanartFilename] = Proxy.Media(fanartData)
			Log('Found fanart image at ' + fanartFilename)

		nfoFile = self.getRelatedFile(path1, '.nfo')
		Log('Looking for Movie NFO file at ' + nfoFile)

		if not os.path.exists(nfoFile):
			Log("ERROR: Can't find .nfo file for " + path1)
		else:
			nfoText = Core.storage.load(nfoFile)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				# Title
				try: metadata.title = nfoXML.xpath('./title')[0].text
				except: pass
				# Original Title
				try: metadata.original_title = nfoXML.xpath('./originaltitle')[0].text
				except: pass
				#summary
				try: metadata.summary = nfoXML.xpath('./plot')[0].text
				except: pass			
				#tagline
				try: metadata.tagline = nfoXML.findall("tagline")[0].text
				except: pass
				#year
				try: metadata.year = int(nfoXML.xpath("year")[0].text)
				except: pass
				#release date
				try:
					try:
						release_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%d %B %Y")
					except:
						release_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%Y-%m-%d")
					if release_date:
						metadata.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(release_date)).date()
				except: pass
				#rating
				try: metadata.rating = float(nfoXML.xpath('./rating')[0].text)
				except: pass
				#content rating
				try: metadata.content_rating = nfoXML.xpath('./mpaa')[0].text
				except: pass
				#director
				try: 
					tempdirector = nfoXML.xpath('./director')[0].text
					directors = tempdirector.split("/")
					if directors != "":
						metadata.directors.clear()
						for r in directors:
							metadata.directors.add(r)
				except: pass
				#studio
				try: metadata.studio = nfoXML.findall("studio")[0].text
				except: pass
				#duration
				try:
					runtime = nfoXML.xpath("runtime")[0].text
					metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
				except: pass
				#genre, cant see mulltiple only sees string not seperate genres
				metadata.genres.clear()
				try:
					genres = nfoXML.xpath('./genre')
					metadata.genres.clear()
					for genreXML in genres:
						gs = genreXML.text.split("/")
						if gs != "":
							for g in gs:
								metadata.genres.add(g)
				except: pass
				#countries
				try:
					countries = nfoXML.xpath('./country')
					metadata.countries.clear()
					for countryXML in countries:
						cs = countryXML.text.split("/")
						if cs != "":
							for c in cs:
								metadata.countries.add(c)
				except: pass
				#actors
				metadata.roles.clear()
				for actor in nfoXML.findall('./actor'):
					role = metadata.roles.new()
					try: role.role = actor.xpath("role")[0].text
					except: pass
					try: role.actor = actor.xpath("name")[0].text
					except: pass
				Log("++++++++++++++++++++++++")
				Log("Movie nfo Information")
				Log("++++++++++++++++++++++++")
				Log("Title: " + str(metadata.title))
				Log("id: " + str(metadata.guid))
				Log("Summary: " + str(metadata.summary))
				Log("Year: " + str(metadata.year))
				Log("IMDB rating: " + str(metadata.rating)) 
				Log("Content Rating: " + str(metadata.content_rating))
				Log("Directors")
				for d in metadata.directors:
					Log("  " + d)
				Log("Studio: " + str(metadata.studio))
				Log("Duration: " + str(metadata.duration))
				Log("Actors")
				for r in metadata.roles:
					try: Log("  " + r.actor + " as " + r.role)
					except: pass
				Log("Genres")
				for r in metadata.genres:
					Log("  " + r)
				Log("++++++++++++++++++++++++")
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")
			return metadata
