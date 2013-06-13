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

##### helper functions #####
	def getRelatedFile(self, videoFile, fileExtension):
		videoFileExtension = videoFile.split(".")[-1]
		return videoFile.replace('.' + videoFileExtension, fileExtension)

	def getMovieNameFromFolder(self, folderpath):
		foldersplit = folderpath.split ('/')
		if foldersplit[-1] == 'VIDEO_TS':
			moviename = '/' + '/'.join(foldersplit[1:len(foldersplit)-1:]) + '/' + re.sub (r' \(.*\)',r'',foldersplit[-2])
		else:
			moviename = '/' + '/'.join(foldersplit) + '/' + re.sub (r' \(.*\)',r'',foldersplit[-1])
		Log("Moviename from folder: " + moviename)
		return moviename

	def checkFilePaths(self, pathfns, ftype):
		for pathfn in pathfns:
			Log("Trying " + pathfn)
			if not os.path.exists(pathfn):
				continue
			else:
				Log("Found " + ftype + " file " + pathfn)
				return pathfn
		else:
			Log("No " + ftype + " file found! Aborting!")

##### search function #####
	def search(self, results, media, lang):
		Log("++++++++++++++++++++++++")
		Log("Entering search function")
		Log("++++++++++++++++++++++++")

		path1 = String.Unquote(media.filename)
		folderpath = os.path.dirname(path1)
		Log('folderpath: ' + folderpath)
		

		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath)

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (folderpath + '/video_ts.nfo')
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (folderpath + '/movie.nfo')
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		nfoNames.append (folderpath + '/' + nfoFiles[0])

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			# work around failing XML parses for things with &'s in
			# them. This may need to go farther than just &'s....
			nfoText = re.sub(r'&([^a-zA-Z#])', r'&amp;\1', nfoText)
			nfoTextLower = nfoText.lower()

			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

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

##### update Function #####
	def update(self, metadata, media, lang):
		Log("++++++++++++++++++++++++")
		Log("Entering update function")
		Log("++++++++++++++++++++++++")

		path1 = media.items[0].parts[0].file
		folderpath = os.path.dirname(path1)
		Log('folderpath: ' + folderpath)

		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath)

		posterData = None
		posterFilename = ""
		posterNames = []
		# Eden
		posterNames.append (self.getRelatedFile(path1, '.tbn'))
		posterNames.append (folderpath + "/folder.jpg")
		# Frodo
		posterNames.append (self.getRelatedFile(path1, '-poster.jpg'))
		posterNames.append (moviename + '-poster.jpg')
		posterNames.append (folderpath + '/poster.jpg')
		posterNames.append (folderpath.replace ('/VIDEO_TS','') + '/poster.jpg')

		# check possible poster file locations
		posterFilename = self.checkFilePaths (posterNames, 'poster')

		if posterFilename:
			posterData = Core.storage.load(posterFilename)
			for key in metadata.posters.keys():
				del metadata.posters[key]

		fanartData = None
		fanartFilename = ""
		fanartNames = []
		# Eden / Frodo
		fanartNames.append (self.getRelatedFile(path1, '-fanart.jpg'))
		fanartNames.append (moviename + '-fanart.jpg')
		fanartNames.append (folderpath + '/fanart.jpg')
		fanartNames.append (folderpath.replace ('/VIDEO_TS','') + '/fanart.jpg')

		# check possible fanart file locations
		fanartFilename = self.checkFilePaths (fanartNames, 'fanart')

		if fanartFilename:
			fanartData = Core.storage.load(fanartFilename)
			for key in metadata.art.keys():
				del metadata.art[key]

		nfoNames = []
		# Eden / Frodo
		nfoNames.append (self.getRelatedFile(path1, '.nfo'))
		nfoNames.append (moviename + '.nfo')
		# VIDEO_TS
		nfoNames.append (folderpath + '/video_ts.nfo')
		# movie.nfo (e.g. FilmInfo!Organizer users)
		nfoNames.append (folderpath + '/movie.nfo')
		# last resort - use first found .nfo
		nfoFiles = [f for f in os.listdir(folderpath) if f.endswith('.nfo')]
		nfoNames.append (folderpath + '/' + nfoFiles[0])

		# check possible .nfo file locations
		nfoFile = self.checkFilePaths (nfoNames, '.nfo')

		if nfoFile:
			nfoText = Core.storage.load(nfoFile)
			nfoText=re.sub(r'&([^a-zA-Z#])',r'&amp;\1',nfoText)
			nfoTextLower = nfoText.lower()
			if nfoTextLower.count('<movie') > 0 and nfoTextLower.count('</movie>') > 0:
				# Remove URLs (or other stuff) at the end of the XML file
				nfoText = '%s</movie>' % nfoText.rsplit('</movie>', 1)[0]

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
				try:
					metadata.content_rating = nfoXML.xpath('./mpaa')[0].text
					if len(metadata.content_rating.split(' ')) > 1:
						valid_mpaa_ratings = ('G', 'PG', 'PG-13', 'R', 'NC-17')
						for mpaa_rating in valid_mpaa_ratings:
							if (' %s ' % mpaa_rating) in metadata.content_rating:
								metadata.content_rating = mpaa_rating
								break
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
				Log("---------------------")
				Log("Movie nfo Information")
				Log("---------------------")
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
				Log("---------------------")
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")
			return metadata
