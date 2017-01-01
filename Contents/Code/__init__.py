# XBMCnfoMoviesImporter
# spec'd from:
#  http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files
#
# Original code author: Harley Hooligan
# Modified by Guillaume Boudreau
# Eden and Frodo compatibility added by Jorge Amigo
# Cleanup and some extensions by SlrG
# Multipart filter idea by diamondsw
# Logo by CrazyRabbit
# Krypton Rating fix by F4RHaD
#
import os
import re
import time
import datetime
import platform
import traceback
import re
import htmlentitydefs
from dateutil.parser import parse

COUNTRY_CODES = {
    'Australia': 'Australia,AU',
    'Canada': 'Canada,CA',
    'France': 'France,FR',
    'Germany': 'Germany,DE',
    'Netherlands': 'Netherlands,NL',
    'United Kingdom': 'UK,GB',
    'United States': 'USA,',
}

PERCENT_RATINGS = {
    'rottentomatoes',
    'rotten tomatoes',
    'rt',
    'flixster',
}

VIDEO_FILE_BASE_REGEX = re.compile(
    r'(?is)\s*\-\s*(cd|dvd|disc|disk|part|pt|d)\s*[0-9]$'
)
MOVIE_NAME_REGEX = re.compile(r' \(.*\)')
UNESCAPE_REGEX = re.compile('&#?\w+;')
NFO_TEXT_REGEX_1 = re.compile(
    r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)'
)
NFO_TEXT_REGEX_2 = re.compile(r'^\s*<.*/>[\r\n]+', flags=re.MULTILINE)
RATING_REGEX_1 = re.compile(
    r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?'
)
RATING_REGEX_2 = re.compile(r'\s*\(.*?\)')

class XBMCNFO(Agent.Movies):
    name = 'XBMCnfoMoviesImporter'
    ver = '1.1-52-g75074b5-158'
    primary_provider = True
    languages = [Locale.Language.NoLanguage]
    accepts_from = [
        'com.plexapp.agents.localmedia',
        'com.plexapp.agents.opensubtitles',
        'com.plexapp.agents.podnapisi',
        'com.plexapp.agents.subzero'
    ]


# ##### helper functions #####
    def debug_log(self, log_message):
        if Prefs['debug']:
            Log.Debug(log_message)

    def get_related_file(self, video_file, file_extension):
        video_file_extension = video_file.split('.')[-1]
        video_file_base = video_file.replace('.' + video_file_extension, '')
        video_file_base = VIDEO_FILE_BASE_REGEX.sub('', video_file_base)
        video_file_base = VIDEO_FILE_BASE_REGEX.sub('', video_file_base)
        return video_file_base + file_extension

    def get_movie_name_from_folder(self, folder_path, with_year):
        folder_split = folder_path.split(os.sep)
        if with_year:
            if folder_split[-1] == 'VIDEO_TS':
                movie_name = os.sep.join(folder_split[1:len(folder_split)-1:]) + os.sep + folder_split[-2]
            else:
                movie_name = os.sep.join(folder_split) + os.sep + folder_split[-1]
            self.debug_log('Movie name from folder'
                           ' (with year): {name}'.format(name=movie_name))
        else:
            if folder_split[-1] == 'VIDEO_TS':
                movie_name = os.sep.join(folder_split[1:len(folder_split)-1:]) + os.sep + MOVIE_NAME_REGEX.sub('', folder_split[-2])
            else:
                movie_name = os.sep.join(folder_split) + os.sep + MOVIE_NAME_REGEX.sub('', folder_split[-1])
            self.debug_log('Movie name from folder:'
                           ' {name}'.format(name=movie_name))
        return movie_name

    def check_file_paths(self, path_fns, f_type):
        for path_fn in path_fns:
            self.debug_log('Trying {name}'.format(name=path_fn))
            if not os.path.exists(path_fn):
                continue
            else:
                Log('Found {type} file {name}'.format(type=f_type, 
                                                      name=path_fn))
                return path_fn
        else:
            Log('No {type} file found! Aborting!'.format(type=f_type))

    def remove_empty_tags(self, xml_tags):
        for xml_tag in xml_tags.iter('*'):
            if len(xml_tag):
                continue
            if not (xml_tag.text and xml_tag.text.strip()):
                # self.debug_log('Removing empty XMLTag: ' + xmltag.tag)
                xml_tag.getparent().remove(xml_tag)
        return xml_tags

    def unescape(self, markup):
        """
        Removes HTML or XML character references and entities from a text.
        Copyright:
            http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
        :param markup: The HTML (or XML) source text.
        :return: The plain text, as a Unicode string, if necessary.
        """
        def fix_up(m):
            text = m.group(0)
            if text[:2] == '&#':
                # character reference
                try:
                    if text[:3] == '&#x':
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text  # leave as is
        return UNESCAPE_REGEX.sub(fix_up, markup)

# ##### search function #####
    def search(self, results, media, lang):
        self.debug_log('++++++++++++++++++++++++')
        self.debug_log('Entering search function')
        self.debug_log('++++++++++++++++++++++++')
        Log('{plugin} Version: {number}'.format(plugin=self.name, 
                                                number=self.ver))
        path1 = media.items[0].parts[0].file
        self.debug_log('media file: {name}'.format(name=path1))
        folder_path = os.path.dirname(path1)
        self.debug_log('folder path: {name}'.format(name=folder_path))

        # Movie name with year from folder
        movie_name_with_year = self.get_movie_name_from_folder(folder_path, True)
        # Movie name from folder
        movie_name = self.get_movie_name_from_folder(folder_path, False)

        nfo_names = []
        # Eden / Frodo
        nfo_names.append(self.get_related_file(path1, '.nfo'))
        nfo_names.append('{movie}.nfo'.format(movie=movie_name_with_year))
        nfo_names.append('{movie}.nfo'.format(movie=movie_name))
        # VIDEO_TS
        nfo_names.append(os.path.join(folder_path, 'video_ts.nfo'))
        # movie.nfo (e.g. FilmInfo!Organizer users)
        nfo_names.append(os.path.join(folder_path, 'movie.nfo'))
        # last resort - use first found .nfo
        nfo_files = [f for f in os.listdir(folder_path) if f.endswith('.nfo')]
        if nfo_files:
            nfo_names.append(os.path.join(folder_path, nfo_files[0]))

        # check possible .nfo file locations
        nfo_file = self.check_file_paths(nfo_names, '.nfo')

        if nfo_file:
            nfo_text = Core.storage.load(nfo_file)
            # work around failing XML parses for things with &'s in
            # them. This may need to go farther than just &'s....
            nfo_text = NFO_TEXT_REGEX_1.sub('&amp;', nfo_text)
            # remove empty xml tags from nfo
            self.debug_log('Removing empty XML tags from movies nfo...')
            nfo_text = NFO_TEXT_REGEX_2.sub('', nfo_text)

            nfo_text_lower = nfo_text.lower()
            if nfo_text_lower.count('<movie') > 0 and nfo_text_lower.count('</movie>') > 0:
                # Remove URLs (or other stuff) at the end of the XML file
                nfo_text = '{content}</movie>'.format(
                    content=nfo_text.rsplit('</movie>', 1)[0]
                )

                # likely an xbmc nfo file
                try:
                    nfo_xml = XML.ElementFromString(nfo_text).xpath('//movie')[0]
                except:
                    self.debug_log('ERROR: Cant parse XML in {nfo}.'
                                   ' Aborting!'.format(nfo=nfo_file))
                    return

                # Title
                try:
                    media.name = nfo_xml.xpath('title')[0].text
                except:
                    self.debug_log('ERROR: No <title> tag in {nfo}.'
                                   ' Aborting!'.format(nfo=nfo_file))
                    return
                # Sort Title
                try:
                    media.title_sort = nfo_xml.xpath('sorttitle')[0].text
                except:
                    self.debug_log('No <sorttitle> tag'
                                   ' in {nfo}.'.format(nfo=nfo_file))
                    pass
                # Year
                try:
                    media.year = int(nfo_xml.xpath('year')[0].text.strip())
                    self.debug_log('Reading year tag:'
                                   ' {year}'.format(year=media.year))
                except:
                    pass
                # ID
                try:
                    id = nfo_xml.xpath('id')[0].text.strip()
                except:
                    id = ''
                    pass
                if len(id) > 2:
                        media.id = id
                        self.debug_log('ID from nfo: {id}'.format(id=media.id))
                else:
                    # if movie id doesn't exist, create
                    # one based on hash of title and year
                    def ord3(x):
                        return '%.3d' % ord(x)
                    id = int(''.join(map(ord3, media.name+str(media.year))))
                    id = str(abs(hash(int(id))))
                    media.id = id
                    self.debug_log('ID generated: {id}'.format(id=media.id))

                results.Append(MetadataSearchResult(id=media.id, name=media.name, year=media.year, lang=lang, score=100))
                try:
                    Log('Found movie information in NFO file:'
                        ' title = {nfo.name},'
                        ' year = {nfo.year},'
                        ' id = {nfo.id}'.format(nfo=media))
                except:
                    pass
            else:
                Log('ERROR: No <movie> tag in {nfo}.'
                    ' Aborting!'.format(nfo=nfo_file))

# ##### update Function #####
    def update(self, metadata, media, lang):
        self.debug_log('++++++++++++++++++++++++')
        self.debug_log('Entering update function')
        self.debug_log('++++++++++++++++++++++++')
        Log('{plugin} Version: {number}'.format(plugin=self.name, 
                                                number=self.ver))

        path1 = media.items[0].parts[0].file
        self.debug_log('media file: {name}'.format(name=path1))
        folder_path = os.path.dirname(path1)
        self.debug_log('folder path: {name}'.format(name=folder_path))

        is_dvd = os.path.basename(folder_path).upper() == 'VIDEO_TS'
        if is_dvd:
            folder_path_dvd = os.path.dirname(folder_path)

        # Movie name with year from folder
        movie_name_with_year = self.get_movie_name_from_folder(folder_path, True)
        # Movie name from folder
        movie_name = self.get_movie_name_from_folder(folder_path, False)

        if not Prefs['localmediaagent']:
            poster_data = None
            poster_filename = ''
            poster_names = []
            # Frodo
            poster_names.append(self.get_related_file(path1, '-poster.jpg'))
            poster_names.append('{movie}-poster.jpg'.format(movie=movie_name_with_year))
            poster_names.append('{movie}-poster.jpg'.format(movie=movie_name))
            poster_names.append(os.path.join(folder_path, 'poster.jpg'))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'poster.jpg'))
            # Eden
            poster_names.append(self.get_related_file(path1, '.tbn'))
            poster_names.append('{path}/folder.jpg'.format(path=folder_path))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'folder.jpg'))
            # DLNA
            poster_names.append(self.get_related_file(path1, '.jpg'))
            # Others
            poster_names.append('{path}/cover.jpg'.format(path=folder_path))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'cover.jpg'))
            poster_names.append('{path}/default.jpg'.format(path=folder_path))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'default.jpg'))
            poster_names.append('{path}/movie.jpg'.format(path=folder_path))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'movie.jpg'))

            # check possible poster file locations
            poster_filename = self.check_file_paths(poster_names, 'poster')

            if poster_filename:
                poster_data = Core.storage.load(poster_filename)
                for key in metadata.posters.keys():
                    del metadata.posters[key]

            fanart_data = None
            fanart_filename = ''
            fanart_names = []
            # Eden / Frodo
            fanart_names.append(self.get_related_file(path1, '-fanart.jpg'))
            fanart_names.append('{movie}-fanart.jpg'.format(movie=movie_name_with_year))
            fanart_names.append('{movie}-fanart.jpg'.format(movie=movie_name))
            fanart_names.append(os.path.join(folder_path, 'fanart.jpg'))
            if is_dvd:
                fanart_names.append(os.path.join(folder_path_dvd, 'fanart.jpg'))
            # Others
            fanart_names.append(os.path.join(folder_path, 'art.jpg'))
            if is_dvd:
                fanart_names.append(os.path.join(folder_path_dvd, 'art.jpg'))
            fanart_names.append(os.path.join(folder_path, 'backdrop.jpg'))
            if is_dvd:
                fanart_names.append(os.path.join(folder_path_dvd, 'backdrop.jpg'))
            fanart_names.append(os.path.join(folder_path, 'background.jpg'))
            if is_dvd:
                fanart_names.append(os.path.join(folder_path_dvd, 'background.jpg'))

            # check possible fanart file locations
            fanart_filename = self.check_file_paths(fanart_names, 'fanart')

            if fanart_filename:
                fanart_data = Core.storage.load(fanart_filename)
                for key in metadata.art.keys():
                    del metadata.art[key]

        nfo_names = []
        # Eden / Frodo
        nfo_names.append(self.get_related_file(path1, '.nfo'))
        nfo_names.append('{movie}.nfo'.format(movie=movie_name_with_year))
        nfo_names.append('{movie}.nfo'.format(movie=movie_name))
        # VIDEO_TS
        nfo_names.append(os.path.join(folder_path, 'video_ts.nfo'))
        # movie.nfo (e.g. FilmInfo!Organizer users)
        nfo_names.append(os.path.join(folder_path, 'movie.nfo'))
        # last resort - use first found .nfo
        nfo_files = [f for f in os.listdir(folder_path) if f.endswith('.nfo')]
        if nfo_files:
            nfo_names.append(os.path.join(folder_path, nfo_files[0]))

        # check possible .nfo file locations
        nfo_file = self.check_file_paths(nfo_names, '.nfo')

        if nfo_file:
            nfo_text = Core.storage.load(nfo_file)
            # work around failing XML parses for things with &'s in
            # them. This may need to go farther than just &'s....
            nfo_text = NFO_TEXT_REGEX_1.sub(r'&amp;', nfo_text)
            # remove empty xml tags from nfo
            self.debug_log('Removing empty XML tags from movies nfo...')
            nfo_text = NFO_TEXT_REGEX_2.sub('', nfo_text)

            nfo_text_lower = nfo_text.lower()
            if nfo_text_lower.count('<movie') > 0 and nfo_text_lower.count('</movie>') > 0:
                # Remove URLs (or other stuff) at the end of the XML file
                nfo_text = '{content}</movie>'.format(
                    content=nfo_text.rsplit('</movie>', 1)[0]
                )

                # likely an xbmc nfo file
                try:
                    nfo_xml = XML.ElementFromString(nfo_text).xpath('//movie')[0]
                except:
                    self.debug_log('ERROR: Cant parse XML in {nfo}.'
                                   ' Aborting!'.format(nfo=nfo_file))
                    return

                # remove empty xml tags
                self.debug_log('Removing empty XML tags from movies nfo...')
                nfo_xml = self.remove_empty_tags(nfo_xml)

                # Title
                try:
                    metadata.title = nfo_xml.xpath('title')[0].text.strip()
                except:
                    self.debug_log('ERROR: No <title> tag in {nfo}.'
                                   ' Aborting!'.format(nfo=nfo_file))
                    return
                # Sort Title
                try:
                    metadata.title_sort = nfo_xml.xpath('sorttitle')[0].text.strip()
                except:
                    self.debug_log('No <sorttitle> tag'
                                   ' in {nfo}.'.format(nfo=nfo_file))
                    pass
                # Year
                try:
                    metadata.year = int(nfo_xml.xpath('year')[0].text.strip())
                    self.debug_log('Set year tag:'
                                   ' {year}'.format(year=metadata.year))
                except:
                    pass
                # Original Title
                try:
                    metadata.original_title = nfo_xml.xpath('originaltitle')[0].text.strip()
                except:
                    pass
                # Content Rating
                metadata.content_rating = ''
                content_rating = {}
                mpaa_rating = ''
                try:
                    mpaa_text = nfo_xml.xpath('./mpaa')[0].text.strip()
                    match = RATING_REGEX_1.match(mpaa_text)
                    if match.group('mpaa'):
                        mpaa_rating = match.group('mpaa')
                        self.debug_log('MPAA Rating: ' + mpaa_rating)
                except:
                    pass
                try:
                    for cert in nfo_xml.xpath('certification')[0].text.split(' / '):
                        country = cert.strip()
                        country = country.split(':')
                        if not country[0] in content_rating:
                            if country[0] == 'Australia':
                                if country[1] == 'MA':
                                    country[1] = 'MA15'
                                if country[1] == 'R':
                                    country[1] = 'R18'
                                if country[1] == 'X':
                                    country[1] = 'X18'
                            if country[0] == 'DE':
                                country[0] = 'Germany'
                            content_rating[country[0]] = country[1].strip('+').replace('FSK', '').replace('ab ', '').strip()
                    self.debug_log('Content Rating(s): ' + str(content_rating))
                except:
                    pass
                if Prefs['country'] != '':
                    cc = COUNTRY_CODES[Prefs['country']].split(',')
                    self.debug_log('Country code from settings:'
                                   ' {name}:{code}'.format(
                        name=Prefs['country'], code=cc)
                    )
                    if cc[0] in content_rating:
                        if cc[1] == '':
                            metadata.content_rating = content_rating.get(cc[0])
                        else:
                            metadata.content_rating = '{country}/{rating}'.format(
                                country=cc[1].lower(),
                                rating=content_rating.get(cc[0]))
                if metadata.content_rating == '' and mpaa_rating != '':
                    metadata.content_rating = mpaa_rating
                if metadata.content_rating == '' and 'USA' in content_rating:
                    metadata.content_rating = content_rating.get('USA')
                if metadata.content_rating == '' or metadata.content_rating == 'Not Rated':
                    metadata.content_rating = 'NR'
                if '(' in metadata.content_rating:
                    metadata.content_rating = RATING_REGEX_2.sub(
                        '', metadata.content_rating
                    )

                # Studio
                try:
                    metadata.studio = nfo_xml.xpath('studio')[0].text.strip()
                except:
                    pass
                # Premiere
                try:
                    release_string = None
                    release_date = None
                    try:
                        self.debug_log('Reading releasedate tag...')
                        release_string = nfo_xml.xpath('releasedate')[0].text.strip()
                        self.debug_log('Releasedate tag is: {value}'.format(value=release_string))
                    except:
                        self.debug_log('No releasedate tag found...')
                        pass
                    if not release_string:
                        try:
                            self.debug_log('Reading premiered tag...')
                            release_string = nfo_xml.xpath('premiered')[0].text.strip()
                            self.debug_log('Premiered tag is: {value}'.format(value=release_string))
                        except:
                            self.debug_log('No premiered tag found...')
                            pass
                    if not release_string:
                        try:
                            self.debug_log('Reading date added tag...')
                            release_string = nfo_xml.xpath('dateadded')[0].text.strip()
                            self.debug_log('Dateadded tag is: {value}'.format(value=release_string))
                        except:
                            self.debug_log('No dateadded tag found...')
                            pass
                    if release_string:
                        try:
                            if Prefs['dayfirst']:
                                dt = parse(release_string, dayfirst=True)
                            else:
                                dt = parse(release_string)
                            release_date = dt
                            self.debug_log('Set premiere to: {date}'.format(
                                date=dt.strftime('%Y-%m-%d')))
                            if not metadata.year:
                                metadata.year = int(dt.strftime('%Y'))
                                self.debug_log('Set year tag from premiere: {year}'.format(year=metadata.year))
                        except:
                            self.debug_log('Couldn\'t parse premiere: {release}'.format(release=air_string))
                            pass
                except:
                    Log.Exception('Exception parsing release date')
                try:
                    if not release_date:
                        self.debug_log('Fallback to year tag instead...')
                        release_date = time.strptime(str(metadata.year) + '-01-01', '%Y-%m-%d')
                        metadata.originally_available_at = datetime.datetime.fromtimestamp(time.mktime(release_date)).date()
                    else:
                        self.debug_log('Setting release date...')
                        metadata.originally_available_at = release_date
                except:
                    pass

                # Tagline
                try:
                    metadata.tagline = nfo_xml.xpath('tagline')[0].text.strip()
                except:
                    pass
                # Summary (Outline/Plot)
                try:
                    if Prefs['plot']:
                        self.debug_log('User setting forces plot before outline...')
                        s_type_1 = 'plot'
                        s_type_2 = 'outline'
                    else:
                        self.debug_log('Default setting forces outline before plot...')
                        s_type_1 = 'outline'
                        s_type_2 = 'plot'
                    try:
                        summary = nfo_xml.xpath(s_type_1)[0].text.strip('| \t\r\n')
                        if not summary:
                            self.debug_log('No or empty {primary} tag. Fallback to {secondary}...'.format(
                                primary=s_type_1, secondary=s_type_2
                            ))
                            raise
                    except:
                        summary = nfo_xml.xpath(s_type_2)[0].text.strip('| \t\r\n')
                    metadata.summary = summary
                except:
                    self.debug_log('Exception on reading summary!')
                    metadata.summary = ''
                    pass
                # Ratings
                try:
                    nfo_rating = None
                    nfo_rating = round(float(nfo_xml.xpath('rating')[0].text.replace(',', '.')), 1)
                    self.debug_log('Series Rating found: ' + str(nfo_rating))
                except:
                    pass
                if not nfo_rating:
                    self.debug_log('Reading old rating style failed.'
                                   ' Trying new Krypton style.')
                    for ratings in nfo_xml.xpath('ratings'):
                        try:
                            rating = ratings.xpath('rating')[0]
                            nfo_rating = round(float(rating.xpath('value')[0].text.replace(',', '.')), 1)
                            self.debug_log('Krypton style series rating found:'
                                           ' {rating}'.format(rating=nfo_rating))
                        except:
                            self.debug_log('Can\'t read rating from tvshow.nfo.')
                            nfo_rating = 0.0
                            pass
                if Prefs['altratings']:
                    self.debug_log('Searching for additional Ratings...')
                    allowed_ratings = Prefs['ratings']
                    if not allowed_ratings:
                        allowed_ratings = ''
                    add_ratings_string = ''
                    try:
                        add_ratings = nfo_xml.xpath('ratings')
                        self.debug_log('Trying to read additional ratings from .nfo.')
                    except:
                        self.debug_log('Can\'t read additional ratings from .nfo.')
                        pass
                    if add_ratings:
                        for add_rating_xml in add_ratings:
                            for add_rating in add_rating_xml:
                                try:
                                    rating_provider = str(add_rating.attrib['moviedb'])
                                except:
                                    pass
                                    self.debug_log('Skipping additional rating without moviedb attribute!')
                                    continue
                                rating_value = str(add_rating.text.replace(',', '.'))
                                if rating_provider.lower() in PERCENT_RATINGS:
                                    rating_value += '%'
                                if rating_provider in allowed_ratings or allowed_ratings == '':
                                    self.debug_log('adding rating: ' + rating_provider + ': ' + rating_value)
                                    add_ratings_string = add_ratings_string + ' | ' + rating_provider + ': ' + rating_value
                            if add_ratings_string != '':
                                self.debug_log('Putting additional ratings at'
                                               ' the {position} of the'
                                               ' summary!'.format(
                                    position=Prefs['ratingspos']))
                                if Prefs['ratingspos'] == 'front':
                                    if Prefs['preserverating']:
                                        metadata.summary = add_ratings_string[3:] + self.unescape(' &#9733;\n\n') + metadata.summary
                                    else:
                                        metadata.summary = self.unescape('&#9733; ') + add_ratings_string[3:] + self.unescape(' &#9733;\n\n') + metadata.summary
                                else:
                                    metadata.summary = metadata.summary + self.unescape('\n\n&#9733; ') + add_ratings_string[3:] + self.unescape(' &#9733;')
                            else:
                                self.debug_log('Additional ratings empty or malformed!')
                if Prefs['preserverating']:
                    self.debug_log('Putting .nfo rating in front of summary!')
                    if not nfo_rating:
                        nfo_rating = 0.0
                    metadata.summary = self.unescape(str(Prefs['beforerating'])) + '{:.1f}'.format(nfo_rating) + self.unescape(str(Prefs['afterrating'])) + metadata.summary
                    metadata.rating = nfo_rating
                else:
                    metadata.rating = nfo_rating
                # Writers (Credits)
                try:
                    credits = nfo_xml.xpath('credits')
                    metadata.writers.clear()
                    for creditXML in credits:
                        for c in creditXML.text.split('/'):
                            metadata.writers.new().name = c.strip()
                except:
                    pass
                # Directors
                try:
                    directors = nfo_xml.xpath('director')
                    metadata.directors.clear()
                    for directorXML in directors:
                        for d in directorXML.text.split('/'):
                            metadata.directors.new().name = d.strip()
                except:
                    pass
                # Genres
                try:
                    genres = nfo_xml.xpath('genre')
                    metadata.genres.clear()
                    [metadata.genres.add(g.strip()) for genreXML in genres for g in genreXML.text.split('/')]
                    metadata.genres.discard('')
                except:
                    pass
                # Countries
                try:
                    countries = nfo_xml.xpath('country')
                    metadata.countries.clear()
                    [metadata.countries.add(c.strip()) for countryXML in countries for c in countryXML.text.split('/')]
                    metadata.countries.discard('')
                except:
                    pass
                # Collections (Set)
                try:
                    sets = nfo_xml.xpath('set')
                    metadata.collections.clear()
                    [metadata.collections.add(s.strip()) for setXML in sets for s in setXML.text.split('/')]
                except:
                    pass
                # Duration
                try:
                    self.debug_log('Trying to read <durationinseconds> tag from .nfo file...')
                    file_info_xml = XML.ElementFromString(nfo_text).xpath('fileinfo')[0]
                    stream_details_xml = file_info_xml.xpath('streamdetails')[0]
                    video_xml = stream_details_xml.xpath('video')[0]
                    runtime = video_xml.xpath('durationinseconds')[0].text.strip()
                    metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 1000  # s
                except:
                    try:
                        self.debug_log('Fallback to <runtime> tag from .nfo file...')
                        runtime = nfo_xml.xpath('runtime')[0].text.strip()
                        metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000  # ms
                    except:
                        self.debug_log('No Duration in .nfo file.')
                        pass
                # Actors
                metadata.roles.clear()
                for actor in nfo_xml.xpath('actor'):
                    role = metadata.roles.new()
                    try:
                        role.name = actor.xpath('name')[0].text
                    except:
                        role.name = 'unknown'
                    try:
                        role.role = actor.xpath('role')[0].text
                    except:
                        role.role = 'unknown'
                    try:
                        role.photo = actor.xpath('thumb')[0].text
                    except:
                        pass

                if not Prefs['localmediaagent']:
                    # Remote posters and fanarts are disabled for now; having them seems to stop the local artworks from being used.
                    # (remote) posters
                    # (local) poster
                    if poster_data:
                        metadata.posters[poster_filename] = Proxy.Media(poster_data)
                    # (remote) fanart
                    # (local) fanart
                    if fanart_data:
                        metadata.art[fanart_filename] = Proxy.Media(fanart_data)

                    # Trailer Support
                    # Eden / Frodo
                    if Prefs['trailer']:
                        for f in os.listdir(folder_path):
                            (fn, ext) = os.path.splitext(f)
                            try:
                                title = ''
                                if fn.endswith('-trailer'):
                                        title = ' '.join(fn.split('-')[:-1])
                                if fn == 'trailer' or f.startswith('movie-trailer'):
                                        title = metadata.title
                                if title != '':
                                    metadata.extras.add(TrailerObject(title=title, file=os.path.join(folder_path, f)))
                                    self.debug_log('Found trailer file ' + os.path.join(folder_path, f))
                                    self.debug_log('Trailer title:' + title)
                            except:
                                self.debug_log('Exception adding trailer file!')


                Log('---------------------')
                Log('Movie nfo Information')
                Log('---------------------')
                try:
                    Log('ID: ' + str(metadata.guid))
                except:
                    Log('ID: -')
                try:
                    Log('Title: ' + str(metadata.title))
                except:
                    Log('Title: -')
                try:
                    Log('Sort Title: ' + str(metadata.title_sort))
                except:
                    Log('Sort Title: -')
                try:
                    Log('Year: ' + str(metadata.year))
                except:
                    Log('Year: -')
                try:
                    Log('Original: ' + str(metadata.original_title))
                except:
                    Log('Original: -')
                try:
                    Log('Rating: ' + str(metadata.rating))
                except:
                    Log('Rating: -')
                try:
                    Log('Content: ' + str(metadata.content_rating))
                except:
                    Log('Content: -')
                try:
                    Log('Studio: ' + str(metadata.studio))
                except:
                    Log('Studio: -')
                try:
                    Log('Premiere: ' + str(metadata.originally_available_at))
                except:
                    Log('Premiere: -')
                try:
                    Log('Tagline: ' + str(metadata.tagline))
                except:
                    Log('Tagline: -')
                try:
                    Log('Summary: ' + str(metadata.summary))
                except:
                    Log('Summary: -')
                Log('Writers:')
                try:
                    [Log('\t' + writer.name) for writer in metadata.writers]
                except:
                    Log('\t-')
                Log('Directors:')
                try:
                    [Log('\t' + director.name) for director in metadata.directors]
                except:
                    Log('\t-')
                Log('Genres:')
                try:
                    [Log('\t' + genre) for genre in metadata.genres]
                except:
                    Log('\t-')
                Log('Countries:')
                try:
                    [Log('\t' + country) for country in metadata.countries]
                except:
                    Log('\t-')
                Log('Collections:')
                try:
                    [Log('\t' + collection) for collection in metadata.collections]
                except:
                    Log('\t-')
                try:
                    Log('Duration: {time} min'.format(
                        time=metadata.duration // 60000))
                except:
                    Log('Duration: -')
                Log('Actors:')
                try:
                    [Log('\t{actor.name} > {actor.role}'.format(actor=actor)
                         for actor in metadata.roles)]
                except:
                    try:
                        [Log('\t{actor.name}'.format(actor=actor)
                             for actor in metadata.roles)]
                    except:
                        Log('\t-')
                Log('---------------------')
            else:
                Log('ERROR: No <movie> tag in {nfo}.'
                    ' Aborting!'.format(nfo=nfo_file))
            return metadata

xbmcnfo = XBMCNFO
