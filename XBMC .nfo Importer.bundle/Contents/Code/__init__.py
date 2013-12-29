# xbmc-nfo importer
# spec'd from: http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
#
import os, re, time, datetime

class xbmcnfo(Agent.Movies):
	name = 'XBMC .nfo Importer'
	primary_provider = True
	languages = [Locale.Language.NoLanguage]
	accepts_from = ['com.plexapp.agents.localmedia']

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
			nfoText = re.sub(r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)', r'&amp;', nfoText)
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
				try: media.name = nfoXML.xpath('title')[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Year
				try: media.year = nfoXML.xpath('year')[0].text
				except: pass
				# ID
				try:
					id = nfoXML.xpath('id')[0].text
					if len(id) > 2:
						media.id = id
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
		isDVD = os.path.basename(folderpath).upper() == 'VIDEO_TS'
		if isDVD: folderpathDVD = os.path.dirname(folderpath)

		# Moviename from folder
		moviename = self.getMovieNameFromFolder (folderpath)

		posterData = None
		posterFilename = ""
		posterNames = []
		# DLNA
		posterNames.append (self.getRelatedFile(path1, '.jpg'))
		# Eden
		posterNames.append (self.getRelatedFile(path1, '.tbn'))
		posterNames.append (folderpath + "/folder.jpg")
		if isDVD: posterNames.append (folderpathDVD + '/folder.jpg')
		# Frodo
		posterNames.append (self.getRelatedFile(path1, '-poster.jpg'))
		posterNames.append (moviename + '-poster.jpg')
		posterNames.append (folderpath + '/poster.jpg')
		if isDVD: posterNames.append (folderpathDVD + '/poster.jpg')
		# Others
		posterNames.append (folderpath + "/cover.jpg")
		if isDVD: posterNames.append (folderpathDVD + '/cover.jpg')
		posterNames.append (folderpath + "/default.jpg")
		if isDVD: posterNames.append (folderpathDVD + '/default.jpg')
		posterNames.append (folderpath + "/movie.jpg")
		if isDVD: posterNames.append (folderpathDVD + '/movie.jpg')

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
		if isDVD: fanartNames.append (folderpathDVD + '/fanart.jpg')
		# Others
		fanartNames.append (folderpath + '/art.jpg')
		if isDVD: fanartNames.append (folderpathDVD + '/art.jpg')
		fanartNames.append (folderpath + '/backdrop.jpg')
		if isDVD: fanartNames.append (folderpathDVD + '/backdrop.jpg')
		fanartNames.append (folderpath + '/background.jpg')
		if isDVD: fanartNames.append (folderpathDVD + '/background.jpg')

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
			nfoText = re.sub(r'&([^a-zA-Z#])',r'&amp;\1',nfoText)
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
				try: metadata.title = nfoXML.xpath('title')[0].text
				except:
					Log("ERROR: No <title> tag in " + nfoFile + ". Aborting!")
					return
				# Year
				try: metadata.year = int(nfoXML.xpath("year")[0].text)
				except: pass
				# Original Title
				try: metadata.original_title = nfoXML.xpath('originaltitle')[0].text
				except: pass
				# Rating
				try: metadata.rating = float(nfoXML.xpath('rating')[0].text.replace(',', '.'))
				except: pass
				# Content Rating
				try:
					mpaa = nfoXML.xpath('./mpaa')[0].text
					match = re.match(r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?', mpaa)
					if match.group('mpaa'):
						content_rating = match.group('mpaa')
					else:
						content_rating = 'NR'
					metadata.content_rating = content_rating
				except: pass
				# Studio
				try: metadata.studio = nfoXML.xpath("studio")[0].text
				except: pass
				# Premiere
				try:
					try:
						release_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%d %B %Y")
					except:
						release_date = time.strptime(nfoXML.xpath("releasedate")[0].text, "%Y-%m-%d")
					except:
						release_date = time.strptime(str(metadata.year) + "-01-01", "%Y-%m-%d") if metadata.year else None
					if release_date:
						metadata.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(release_date)).date()
				except: pass
				# Tagline
				try: metadata.tagline = nfoXML.xpath("tagline")[0].text
				except: pass
				# Summary (Outline/Plot)
				try:
					try:
						summary = nfoXML.xpath('outline')[0].text.strip('| \t\r\n')
						if not summary: raise
					except:
						summary = nfoXML.xpath('plot')[0].text.strip('| \t\r\n')
					metadata.summary = summary
				except: pass
				# Writers (Credits)
				try: 
					credits = nfoXML.xpath('credits')
					metadata.writers.clear()
					[metadata.writers.add(c.strip()) for creditXML in credits for c in creditXML.text.split("/")]
					metadata.writers.discard('')
				except: pass
				# Directors
				try: 
					directors = nfoXML.xpath('director')
					metadata.directors.clear()
					[metadata.directors.add(d.strip()) for directorXML in directors for d in directorXML.text.split("/")]
					metadata.directors.discard('')
				except: pass
				# Genres
				try:
					genres = nfoXML.xpath('genre')
					metadata.genres.clear()
					[metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split("/")]
					metadata.genres.discard('')
				except: pass
				# Countries
				try:
					countries = nfoXML.xpath('country')
					metadata.countries.clear()
					[metadata.countries.add(c.strip()) for countryXML in countries for c in countryXML.text.split("/")]
					metadata.countries.discard('')
				except: pass
				# Collections (Set)
				try:
					sets = nfoXML.xpath('set')
					metadata.collections.clear()
					[metadata.collections.add(s.strip()) for setXML in sets for s in setXML.text.split("/")]
					metadata.collections.discard('')
				except: pass
				# Duration
				try:
					runtime = nfoXML.xpath("runtime")[0].text
					metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000 # ms
				except: pass
				# Actors
				metadata.roles.clear()
				for actor in nfoXML.xpath('actor'):
					role = metadata.roles.new()
					try: role.actor = actor.xpath("name")[0].text
					except: pass
					try: role.role = actor.xpath("role")[0].text
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
				
				# Log("---------------------")
				# Log("Movie nfo Information")
				# Log("---------------------")
				# Log("Title: " + str(metadata.title))
				# Log("id: " + str(metadata.guid))
				# Log("Summary: " + str(metadata.summary))
				# Log("Year: " + str(metadata.year))
				# Log("IMDB rating: " + str(metadata.rating)) 
				# Log("Content Rating: " + str(metadata.content_rating))
				# Log("Directors")
				# for d in metadata.directors:
					# Log("  " + d)
				# Log("Studio: " + str(metadata.studio))
				# Log("Duration: " + str(metadata.duration))
				# Log("Actors")
				# for r in metadata.roles:
					# try: Log("  " + r.actor + " as " + r.role)
					# except: pass
				# Log("Genres")
				# for r in metadata.genres:
					# Log("  " + r)
				# Log("---------------------")
				
				Log("---------------------")
				Log("Movie nfo Information")
				Log("---------------------")
				try: Log("ID: " + str(metadata.guid))
				except: Log("ID: -")
				try: Log("Title: " + str(metadata.title))
				except: Log("Title: -")
				try: Log("Year: " + str(metadata.year))
				except: Log("Year: -")
				try: Log("Original: " + str(metadata.original_title))
				except: Log("Original: -")
				try: Log("Rating: " + str(metadata.rating))
				except: Log("Rating: -")
				try: Log("Content: " + str(metadata.content_rating))
				except: Log("Content: -")
				try: Log("Studio: " + str(metadata.studio))
				except: Log("Studio: -")
				try: Log("Premiere: " + str(metadata.originally_available_at))
				except: Log("Premiere: -")
				try: Log("Tagline: " + str(metadata.tagline))
				except: Log("Tagline: -")
				try: Log("Summary: " + str(metadata.summary))
				except: Log("Summary: -")
				Log("Writers:")
				try: [Log("\t" + writer) for writer in metadata.writers]
				except: Log("\t-")
				Log("Directors:")
				try: [Log("\t" + director) for director in metadata.directors]
				except: Log("\t-")
				Log("Genres:")
				try: [Log("\t" + genre) for genre in metadata.genres]
				except: Log("\t-")
				Log("Countries:")
				try: [Log("\t" + country) for country in metadata.countries]
				except: Log("\t-")
				Log("Collections:")
				try: [Log("\t" + collection) for collection in metadata.collections]
				except: Log("\t-")
				try: Log("Duration: " + str(metadata.duration // 60000) + ' min')
				except: Log("Duration: -")
				Log("Actors:")
				try: [Log("\t" + actor.actor + " > " + actor.role) for actor in metadata.roles]
				except: [Log("\t" + actor.actor) for actor in metadata.roles]
				except: Log("\t-")
				Log("---------------------")
			else:
				Log("ERROR: No <movie> tag in " + nfoFile + ". Aborting!")
			return metadata
