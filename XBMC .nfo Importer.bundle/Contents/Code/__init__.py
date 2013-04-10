# xbmc-nfo importer
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
#
import os, re, time, datetime

class xbmcnfo(Agent.Movies):
	name = 'XBMC .nfo Importer'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]

	def search(self, results, media, lang):
		Log("Searching")

		path1 = String.Unquote(media.filename)
		nfoFile = self.getRelatedFile(path1, '.nfo')
		Log('Looking for Movie NFO file at ' + nfoFile)

		if not os.path.exists(nfoFile):
			Log("ERROR: Can't find .nfo file for " + path1)
			Log("Some users may have movie.nfo files. (FilmInfo!Organizer users for example) We will try this.")
			nfoFile = self.getAlternativeNfoFile(path1)
		if not os.path.exists(nfoFile):
			Log("ERROR: Also can't find " + nfoFile)
		else:
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in
			# them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&([^a-zA-Z#])', r'&amp;\1', nfoText)
			nfoTextLower = nfoText.lower()

			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.split('</movie>')[0]

				# likely an xbmc nfo file
				try: nfoXML = XML.ElementFromString(nfoText).xpath('//movie')[0]
				except:
					Log('ERROR: Cant parse XML in ' + nfoFile + '. Aborting!')
					return

				# Title
				try: media.name = nfoXML.xpath('./title')[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# IMDB id
				try:
					imdb_id = nfoXML.xpath('./id')[0].text
					if len(imdb_id) > 2:
						media.id = imdb_id
				except: pass
				# Year
				try: media.year = nfoXML.xpath('./year')[0].text
				except: pass

				results.Append(MetadataSearchResult(id=media.id, name=media.name, year=media.year, lang=lang, score=100))
				try: Log('Found movie information in NFO file: title = ' + media.name + ', year = ' + str(media.year) + ', id = ' + media.id)
				except: pass
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")

	def getRelatedFile(self, videoFile, fileExtension):
		videoFileExtension = videoFile.split(".")[-1]
		return videoFile.replace('.' + videoFileExtension, fileExtension)
		
	def getAlternativeNfoFile(self, videoFile):
		return os.path.dirname(videoFile) + '\movie.nfo'
	
	def update(self, metadata, media, lang):
		path1 = media.items[0].parts[0].file
		folderpath = os.path.dirname(path1)

		posterData = None
		posterFilenameEden = self.getRelatedFile(path1, '.tbn')
		posterFilenameFrodo = self.getRelatedFile(path1, '-poster.jpg')
		posterFilenameInFolderEden = folderpath + "/folder.jpg"
		posterFilenameInFolderFrodo = folderpath + "/poster.jpg"
		posterFilename = ""
		if os.path.exists(posterFilenameInFolderEden):
			posterFilename = posterFilenameInFolderEden
		if os.path.exists(posterFilenameInFolderFrodo):
			posterFilename = posterFilenameInFolderFrodo
		if os.path.exists(posterFilenameEden):
			posterFilename = posterFilenameEden
		if os.path.exists(posterFilenameFrodo):
			posterFilename = posterFilenameFrodo
		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			for key in metadata.posters.keys():
				del metadata.posters[key]
			Log('Found poster image at ' + posterFilename)

		fanartData = None
		fanartFilenameEden = self.getRelatedFile(path1, '-fanart.jpg')
		fanartFilenameInFolderFrodo = folderpath + '/fanart.jpg'
		fanartFilename = ""
		if os.path.exists(fanartFilenameEden):
			fanartFilename = fanartFilenameEden
		if os.path.exists(fanartFilenameInFolderFrodo):
			fanartFilename = fanartFilenameInFolderFrodo
		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			for key in metadata.art.keys():
				del metadata.art[key]
			Log('Found fanart image at ' + fanartFilename)

		nfoFile = self.getRelatedFile(path1, '.nfo')
		Log('Looking for Movie NFO file at ' + nfoFile)

		if not os.path.exists(nfoFile):
			Log("ERROR: Can't find .nfo file for " + path1)
			Log("Some users may have movie.nfo files. (FilmInfo!Organizer users for example) We will try this.")
			nfoFile = self.getAlternativeNfoFile(path1)
		if not os.path.exists(nfoFile):
			Log("ERROR: Also can't find " + nfoFile)
		else:
			nfoText = Core.storage.load(nfoFile)
			nfoText=re.sub(r'&([^a-zA-Z#])',r'&amp;\1',nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.split('</movie>')[0]

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
						try:
							release_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%Y-%m-%d")
						except:
							if metadata.year:
								release_date = time.strptime(str(metadata.year) + "-01-01", "%Y-%m-%d")
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
					directors = nfoXML.xpath('./director')
					metadata.directors.clear()
					for directorXML in directors:
						ds = directorXML.text.split("/")
						if ds != "":
							for d in ds:
								metadata.directors.add(d)
				except: pass
				#writers/credits
				try: 
					credits = nfoXML.xpath('./credits')
					metadata.writers.clear()
					for creditXML in credits:
						writer = creditXML.text
						metadata.writers.add(writer)
				except: pass
				#studio
				try: metadata.studio = nfoXML.findall("studio")[0].text
				except: pass
				#duration
				try:
					runtime = nfoXML.xpath("runtime")[0].text
					metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
				except: pass
				#set/collections
				try:
					set_ = nfoXML.xpath('./set')[0].text
					metadata.collections.clear()
					metadata.collections.add(set_)
				except: pass
				#genre, cant see mulltiple only sees string not seperate genres
				try:
					genres = nfoXML.xpath('./genre')
					metadata.genres.clear()
					for genreXML in genres:
						gs = genreXML.text.split("/")
						if gs != "":
							for g in gs:
								metadata.genres.add(g.strip())
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
				# Remote posters and fanarts are disabled for now; having them seems to stop the local artworks from being used.
				#(remote) posters
				#try:
				#	posters = nfoXML.xpath('./thumb')
				#	for posterXML in posters:
				#		url = posterXML.text
				#		previewUrl = posterXML.get('preview')
				#		Log("Found (remote) poster at: " + previewUrl + " > " + url)
				#		metadata.posters[url] = Proxy.Preview(previewUrl)
				#except: pass
				#(local) poster
				if posterData:
					metadata.posters[posterFilename] = Proxy.Media(posterData)
				#(remote) fanart
				#try:
				#	arts = nfoXML.xpath('./fanart/thumb')
				#	for artXML in arts:
				#		url = artXML.text
				#		previewUrl = artXML.get('preview')
				#		Log("Found (remote) fanart at: " + previewUrl + " > " + url)
				#		metadata.art[url] = Proxy.Preview(previewUrl)
				#except: pass
				#(local) fanart
				if fanartData:
					metadata.art[fanartFilename] = Proxy.Media(fanartData)
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
