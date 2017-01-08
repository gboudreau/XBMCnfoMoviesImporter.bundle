# coding=utf-8

"""
XBMCnfoMoviesImporter

spec'd from:
 http://wiki.xbmc.org/index.php?title=Import_-_Export_Library#Video_nfo_Files

CREDITS:
    Original code author: .......... Harley Hooligan
    Modified by: ................... Guillaume Boudreau
    Eden and Frodo compatibility: .. Jorge Amigo
    Cleanup and some extensions: ... SlrG
    Multipart filter idea: ......... diamondsw
    Logo: .......................... CrazyRabbit
    Krypton Rating fix: ............ F4RHaD
    PEP 8 and refactoring: ......... Labrys
"""

from datetime import datetime
import os
import re
import sys
from dateutil.parser import parse

if sys.version_info < (3, 0):
    from htmlentitydefs import name2codepoint
else:
    from html.entities import name2codepoint
    unichr = chr  # chr is already unicode

# PLEX API
preferences = Prefs
element_from_string = XML.ElementFromString
load_file = Core.storage.load
PlexAgent = Agent.Movies
MediaProxy = Proxy.Media
Metadata = MetadataSearchResult
Trailer = TrailerObject

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

NFO_TEXT_REGEX_1 = re.compile(
    r'&(?![A-Za-z]+[0-9]*;|#[0-9]+;|#x[0-9a-fA-F]+;)'
)
NFO_TEXT_REGEX_2 = re.compile(r'^\s*<.*/>[\r\n]+', flags=re.MULTILINE)
RATING_REGEX_1 = re.compile(
    r'(?:Rated\s)?(?P<mpaa>[A-z0-9-+/.]+(?:\s[0-9]+[A-z]?)?)?'
)
RATING_REGEX_2 = re.compile(r'\s*\(.*?\)')


class XBMCNFO(PlexAgent):
    """
    A Plex Metadata Agent for Movies.

    Uses XBMC nfo files as the metadata source for Plex Movies.
    """
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

# ##### search function #####
    def search(self, results, media, lang):
        log.debug('++++++++++++++++++++++++')
        log.debug('Entering search function')
        log.debug('++++++++++++++++++++++++')

        log.info('{plugin} Version: {number}'.format(
            plugin=self.name, number=self.ver))

        path1 = media.items[0].parts[0].file
        log.debug('media file: {name}'.format(name=path1))

        folder_path = os.path.dirname(path1)
        log.debug('folder path: {name}'.format(name=folder_path))

        # Movie name with year from folder
        movie_name_with_year = get_movie_name_from_folder(folder_path, True)
        # Movie name from folder
        movie_name = get_movie_name_from_folder(folder_path, False)

        nfo_names = [
            # Eden / Frodo
            get_related_file(path1, '.nfo'),
            '{movie}.nfo'.format(movie=movie_name_with_year),
            '{movie}.nfo'.format(movie=movie_name),
            # VIDEO_TS
            os.path.join(folder_path, 'video_ts.nfo'),
            # movie.nfo (e.g. FilmInfo!Organizer users)
            os.path.join(folder_path, 'movie.nfo'),
        ]

        # last resort - use first found .nfo
        nfo_files = (f for f in os.listdir(folder_path) if f.endswith('.nfo'))

        try:
            first_nfo = nfo_files.next()
        except StopIteration:
            log.debug('No NFO found in {path!r}'.format(path=folder_path))
        else:
            nfo_names.append(os.path.join(folder_path, first_nfo))

        # check possible .nfo file locations
        nfo_file = check_file_paths(nfo_names, '.nfo')

        if nfo_file:
            nfo_text = load_file(nfo_file)
            # work around failing XML parses for things with &'s in
            # them. This may need to go farther than just &'s....
            nfo_text = NFO_TEXT_REGEX_1.sub('&amp;', nfo_text)
            # remove empty xml tags from nfo
            log.debug('Removing empty XML tags from movies nfo...')
            nfo_text = NFO_TEXT_REGEX_2.sub('', nfo_text)

            nfo_text_lower = nfo_text.lower()
            if nfo_text_lower.count('<movie') > 0 and nfo_text_lower.count('</movie>') > 0:
                # Remove URLs (or other stuff) at the end of the XML file
                nfo_text = '{content}</movie>'.format(
                    content=nfo_text.rsplit('</movie>', 1)[0]
                )

                # likely an xbmc nfo file
                try:
                    nfo_xml = element_from_string(nfo_text).xpath('//movie')[0]
                except:
                    log.debug('ERROR: Cant parse XML in {nfo}.'
                              ' Aborting!'.format(nfo=nfo_file))
                    return

                # Title
                try:
                    media.name = nfo_xml.xpath('title')[0].text
                except:
                    log.debug('ERROR: No <title> tag in {nfo}.'
                              ' Aborting!'.format(nfo=nfo_file))
                    return
                # Sort Title
                try:
                    media.title_sort = nfo_xml.xpath('sorttitle')[0].text
                except:
                    log.debug('No <sorttitle> tag in {nfo}.'.format(
                        nfo=nfo_file))
                    pass
                # Year
                try:
                    media.year = int(nfo_xml.xpath('year')[0].text.strip())
                    log.debug('Reading year tag: {year}'.format(
                        year=media.year))
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
                        log.debug('ID from nfo: {id}'.format(id=media.id))
                else:
                    # if movie id doesn't exist, create
                    # one based on hash of title and year
                    def ord3(x):
                        return '%.3d' % ord(x)
                    id = int(''.join(map(ord3, media.name+str(media.year))))
                    id = str(abs(hash(int(id))))
                    media.id = id
                    log.debug('ID generated: {id}'.format(id=media.id))

                results.Append(Metadata(id=media.id, name=media.name, year=media.year, lang=lang, score=100))
                try:
                    log.info('Found movie information in NFO file:'
                             ' title = {nfo.name},'
                             ' year = {nfo.year},'
                             ' id = {nfo.id}'.format(nfo=media))
                except:
                    pass
            else:
                log.info('ERROR: No <movie> tag in {nfo}. Aborting!'.format(
                    nfo=nfo_file))

# ##### update Function #####

    def update(self, metadata, media, lang):
        log.debug('++++++++++++++++++++++++')
        log.debug('Entering update function')
        log.debug('++++++++++++++++++++++++')

        poster_data = None
        poster_filename = None
        fanart_data = None
        fanart_filename = None

        log.info('{plugin} Version: {number}'.format(
            plugin=self.name, number=self.ver))

        path1 = media.items[0].parts[0].file
        log.debug('media file: {name}'.format(name=path1))

        folder_path = os.path.dirname(path1)
        log.debug('folder path: {name}'.format(name=folder_path))

        is_dvd = os.path.basename(folder_path).upper() == 'VIDEO_TS'
        folder_path_dvd = os.path.dirname(folder_path) if is_dvd else None

        # Movie name with year from folder
        movie_name_with_year = get_movie_name_from_folder(folder_path, True)

        # Movie name from folder
        movie_name = get_movie_name_from_folder(folder_path, False)

        if not preferences['localmediaagent']:
            poster_names = [
                # Frodo
                get_related_file(path1, '-poster.jpg'),
                '{movie}-poster.jpg'.format(movie=movie_name_with_year),
                '{movie}-poster.jpg'.format(movie=movie_name),
                os.path.join(folder_path, 'poster.jpg'),
            ]
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'poster.jpg'))
            # Eden
            poster_names.append(get_related_file(path1, '.tbn'))
            poster_names.append('{path}/folder.jpg'.format(path=folder_path))
            if is_dvd:
                poster_names.append(os.path.join(folder_path_dvd, 'folder.jpg'))
            # DLNA
            poster_names.append(get_related_file(path1, '.jpg'))
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
            poster_filename = check_file_paths(poster_names, 'poster')

            if poster_filename:
                poster_data = load_file(poster_filename)
                for key in metadata.posters.keys():
                    del metadata.posters[key]

            fanart_names = [
                # Eden / Frodo
                get_related_file(path1, '-fanart.jpg'),
                '{movie}-fanart.jpg'.format(movie=movie_name_with_year),
                '{movie}-fanart.jpg'.format(movie=movie_name),
                os.path.join(folder_path, 'fanart.jpg'),
            ]
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
            fanart_filename = check_file_paths(fanart_names, 'fanart')

            if fanart_filename:
                fanart_data = load_file(fanart_filename)
                for key in metadata.art.keys():
                    del metadata.art[key]

        nfo_names = [
            # Eden / Frodo
            get_related_file(path1, '.nfo'),
            '{movie}.nfo'.format(movie=movie_name_with_year),
            '{movie}.nfo'.format(movie=movie_name),
            # VIDEO_TS
            os.path.join(folder_path, 'video_ts.nfo'),
            # movie.nfo (e.g. FilmInfo!Organizer users)
            os.path.join(folder_path, 'movie.nfo'),
        ]

        # last resort - use first found .nfo
        nfo_files = (f for f in os.listdir(folder_path) if f.endswith('.nfo'))

        try:
            first_nfo = nfo_files.next()
        except StopIteration:
            log.debug('No NFO file found in {path!r}'.format(path=folder_path))
        else:
            nfo_names.append(os.path.join(folder_path, first_nfo))

        # check possible .nfo file locations
        nfo_file = check_file_paths(nfo_names, '.nfo')

        if nfo_file:
            nfo_text = load_file(nfo_file)

            # work around failing XML parses for things with &'s in
            # them. This may need to go farther than just &'s....
            nfo_text = NFO_TEXT_REGEX_1.sub(r'&amp;', nfo_text)

            # remove empty xml tags from nfo
            log.debug('Removing empty XML tags from movies nfo...')
            nfo_text = NFO_TEXT_REGEX_2.sub('', nfo_text)

            nfo_text_lower = nfo_text.lower()

            if nfo_text_lower.count('<movie') > 0 and nfo_text_lower.count('</movie>') > 0:
                # Remove URLs (or other stuff) at the end of the XML file
                nfo_text = '{content}</movie>'.format(
                    content=nfo_text.rsplit('</movie>', 1)[0]
                )

                # likely an xbmc nfo file
                try:
                    nfo_xml = element_from_string(nfo_text).xpath('//movie')[0]
                except:
                    log.debug('ERROR: Cant parse XML in {nfo}.'
                              ' Aborting!'.format(nfo=nfo_file))
                    return

                # remove empty xml tags
                log.debug('Removing empty XML tags from movies nfo...')
                nfo_xml = remove_empty_tags(nfo_xml)

                # Title
                try:
                    metadata.title = nfo_xml.xpath('title')[0].text.strip()
                except:
                    log.debug('ERROR: No <title> tag in {nfo}.'
                              ' Aborting!'.format(nfo=nfo_file))
                    return
                # Sort Title
                try:
                    metadata.title_sort = nfo_xml.xpath('sorttitle')[0].text.strip()
                except:
                    log.debug('No <sorttitle> tag in {nfo}.'.format(
                        nfo=nfo_file))
                    pass
                # Year
                try:
                    metadata.year = int(nfo_xml.xpath('year')[0].text.strip())
                    log.debug('Set year tag: {year}'.format(
                        year=metadata.year))
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
                        log.debug('MPAA Rating: ' + mpaa_rating)
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
                    log.debug('Content Rating(s): ' + str(content_rating))
                except:
                    pass
                if preferences['country'] != '':
                    cc = COUNTRY_CODES[preferences['country']].split(',')
                    log.debug(
                        'Country code from settings: {name}:{code}'.format(
                            name=preferences['country'], code=cc))
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
                release_string = None
                release_date = None
                try:
                    try:
                        log.debug('Reading releasedate tag...')
                        release_string = nfo_xml.xpath('releasedate')[0].text.strip()
                        log.debug('Releasedate tag is: {value}'.format(value=release_string))
                    except:
                        log.debug('No releasedate tag found...')
                        pass
                    if not release_string:
                        try:
                            log.debug('Reading premiered tag...')
                            release_string = nfo_xml.xpath('premiered')[0].text.strip()
                            log.debug('Premiered tag is: {value}'.format(value=release_string))
                        except:
                            log.debug('No premiered tag found...')
                            pass
                    if not release_string:
                        try:
                            log.debug('Reading date added tag...')
                            release_string = nfo_xml.xpath('dateadded')[0].text.strip()
                            log.debug('Dateadded tag is: {value}'.format(value=release_string))
                        except:
                            log.debug('No dateadded tag found...')
                            pass
                    if release_string:
                        try:
                            if preferences['dayfirst']:
                                dt = parse(release_string, dayfirst=True)
                            else:
                                dt = parse(release_string)
                            release_date = dt
                            log.debug('Set premiere to: {date}'.format(
                                date=dt.strftime('%Y-%m-%d')))
                            if not metadata.year:
                                metadata.year = int(dt.strftime('%Y'))
                                log.debug('Set year tag from premiere: {year}'.format(year=metadata.year))
                        except:
                            log.debug('Couldn\'t parse premiere: {release}'.format(release=release_string))
                            pass
                except:
                    log.exception('Exception parsing release date')
                try:
                    if not release_date:
                        log.debug('Fallback to year tag instead...')
                        release_date = datetime(int(metadata.year), 1, 1).date()
                        metadata.originally_available_at = release_date
                    else:
                        log.debug('Setting release date...')
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
                    if preferences['plot']:
                        log.debug('User setting forces plot before outline...')
                        s_type_1 = 'plot'
                        s_type_2 = 'outline'
                    else:
                        log.debug('Default setting forces outline before plot...')
                        s_type_1 = 'outline'
                        s_type_2 = 'plot'
                    try:
                        summary = nfo_xml.xpath(s_type_1)[0].text.strip('| \t\r\n')
                        if not summary:
                            log.debug('No or empty {primary} tag. Fallback to {secondary}...'.format(
                                primary=s_type_1, secondary=s_type_2
                            ))
                            raise
                    except:
                        summary = nfo_xml.xpath(s_type_2)[0].text.strip('| \t\r\n')
                    metadata.summary = summary
                except:
                    log.debug('Exception on reading summary!')
                    metadata.summary = ''
                    pass
                # Ratings
                nfo_rating = None
                try:
                    nfo_rating = round(float(nfo_xml.xpath('rating')[0].text.replace(',', '.')), 1)
                    log.debug('Series Rating found: ' + str(nfo_rating))
                except:
                    pass
                if not nfo_rating:
                    log.debug('Reading old rating style failed.'
                              ' Trying new Krypton style.')
                    for ratings in nfo_xml.xpath('ratings'):
                        try:
                            rating = ratings.xpath('rating')[0]
                            nfo_rating = round(float(rating.xpath('value')[0].text.replace(',', '.')), 1)
                            log.debug('Krypton style series rating found:'
                                      ' {rating}'.format(rating=nfo_rating))
                        except:
                            log.debug('Can\'t read rating from tvshow.nfo.')
                            nfo_rating = 0.0
                            pass
                if preferences['altratings']:
                    log.debug('Searching for additional Ratings...')
                    allowed_ratings = preferences['ratings']
                    if not allowed_ratings:
                        allowed_ratings = ''
                    add_ratings_string = ''
                    add_ratings = None
                    try:
                        add_ratings = nfo_xml.xpath('ratings')
                        log.debug('Trying to read additional ratings from .nfo.')
                    except:
                        log.debug('Can\'t read additional ratings from .nfo.')
                        pass
                    if add_ratings:
                        for add_rating_xml in add_ratings:
                            for add_rating in add_rating_xml:
                                try:
                                    rating_provider = str(add_rating.attrib['moviedb'])
                                except:
                                    pass
                                    log.debug('Skipping additional rating without moviedb attribute!')
                                    continue
                                rating_value = str(add_rating.text.replace(',', '.'))
                                if rating_provider.lower() in PERCENT_RATINGS:
                                    rating_value += '%'
                                if rating_provider in allowed_ratings or allowed_ratings == '':
                                    log.debug('adding rating: ' + rating_provider + ': ' + rating_value)
                                    add_ratings_string = add_ratings_string + ' | ' + rating_provider + ': ' + rating_value
                            if add_ratings_string != '':
                                log.debug(
                                    'Putting additional ratings at the'
                                    ' {position} of the summary!'.format(
                                        position=preferences['ratingspos'])
                                )
                                if preferences['ratingspos'] == 'front':
                                    if preferences['preserverating']:
                                        metadata.summary = add_ratings_string[3:] + unescape(' &#9733;\n\n') + metadata.summary
                                    else:
                                        metadata.summary = unescape('&#9733; ') + add_ratings_string[3:] + unescape(' &#9733;\n\n') + metadata.summary
                                else:
                                    metadata.summary = metadata.summary + unescape('\n\n&#9733; ') + add_ratings_string[3:] + unescape(' &#9733;')
                            else:
                                log.debug('Additional ratings empty or malformed!')
                if preferences['preserverating']:
                    log.debug('Putting .nfo rating in front of summary!')
                    if not nfo_rating:
                        nfo_rating = 0.0
                    metadata.summary = unescape(str(preferences['beforerating'])) + '{:.1f}'.format(nfo_rating) + unescape(str(preferences['afterrating'])) + metadata.summary
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
                    log.debug('Trying to read <durationinseconds> tag from .nfo file...')
                    file_info_xml = element_from_string(nfo_text).xpath('fileinfo')[0]
                    stream_details_xml = file_info_xml.xpath('streamdetails')[0]
                    video_xml = stream_details_xml.xpath('video')[0]
                    runtime = video_xml.xpath('durationinseconds')[0].text.strip()
                    metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 1000  # s
                except:
                    try:
                        log.debug('Fallback to <runtime> tag from .nfo file...')
                        runtime = nfo_xml.xpath('runtime')[0].text.strip()
                        metadata.duration = int(re.compile('^([0-9]+)').findall(runtime)[0]) * 60 * 1000  # ms
                    except:
                        log.debug('No Duration in .nfo file.')
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

                if not preferences['localmediaagent']:
                    # Remote posters and fanarts are disabled for now; having
                    # them seems to stop the local artworks from being used.
                    # (remote) posters
                    # (local) poster
                    if poster_data:
                        metadata.posters[poster_filename] = MediaProxy(poster_data)
                    # (remote) fanart
                    # (local) fanart
                    if fanart_data:
                        metadata.art[fanart_filename] = MediaProxy(fanart_data)

                    # Trailer Support
                    # Eden / Frodo
                    if preferences['trailer']:
                        for f in os.listdir(folder_path):
                            (fn, ext) = os.path.splitext(f)
                            try:
                                title = ''
                                if fn.endswith('-trailer'):
                                        title = ' '.join(fn.split('-')[:-1])
                                if fn == 'trailer' or f.startswith('movie-trailer'):
                                        title = metadata.title
                                if title != '':
                                    metadata.extras.add(Trailer(title=title, file=os.path.join(folder_path, f)))
                                    log.debug('Found trailer file ' + os.path.join(folder_path, f))
                                    log.debug('Trailer title:' + title)
                            except:
                                log.debug('Exception adding trailer file!')

                log.info('---------------------')
                log.info('Movie nfo Information')
                log.info('---------------------')
                try:
                    log.info('ID: ' + str(metadata.guid))
                except:
                    log.info('ID: -')
                try:
                    log.info('Title: ' + str(metadata.title))
                except:
                    log.info('Title: -')
                try:
                    log.info('Sort Title: ' + str(metadata.title_sort))
                except:
                    log.info('Sort Title: -')
                try:
                    log.info('Year: ' + str(metadata.year))
                except:
                    log.info('Year: -')
                try:
                    log.info('Original: ' + str(metadata.original_title))
                except:
                    log.info('Original: -')
                try:
                    log.info('Rating: ' + str(metadata.rating))
                except:
                    log.info('Rating: -')
                try:
                    log.info('Content: ' + str(metadata.content_rating))
                except:
                    log.info('Content: -')
                try:
                    log.info('Studio: ' + str(metadata.studio))
                except:
                    log.info('Studio: -')
                try:
                    log.info('Premiere: ' + str(metadata.originally_available_at))
                except:
                    log.info('Premiere: -')
                try:
                    log.info('Tagline: ' + str(metadata.tagline))
                except:
                    log.info('Tagline: -')
                try:
                    log.info('Summary: ' + str(metadata.summary))
                except:
                    log.info('Summary: -')
                log.info('Writers:')
                try:
                    [log.info('\t' + writer.name) for writer in metadata.writers]
                except:
                    log.info('\t-')
                log.info('Directors:')
                try:
                    [log.info('\t' + director.name) for director in metadata.directors]
                except:
                    log.info('\t-')
                log.info('Genres:')
                try:
                    [log.info('\t' + genre) for genre in metadata.genres]
                except:
                    log.info('\t-')
                log.info('Countries:')
                try:
                    [log.info('\t' + country) for country in metadata.countries]
                except:
                    log.info('\t-')
                log.info('Collections:')
                try:
                    [log.info('\t' + collection) for collection in metadata.collections]
                except:
                    log.info('\t-')
                try:
                    log.info('Duration: {time} min'.format(
                        time=metadata.duration // 60000))
                except:
                    log.info('Duration: -')
                log.info('Actors:')
                for actor in metadata.roles:
                    try:
                        log.info('\t{actor.name} > {actor.role}'.format(actor=actor))
                    except:
                        try:
                            log.info('\t{actor.name}'.format(actor=actor))
                        except:
                            log.info('\t-')
                    log.info('---------------------')
            else:
                log.info('ERROR: No <movie> tag in {nfo}.'
                         ' Aborting!'.format(nfo=nfo_file))
            return metadata

xbmcnfo = XBMCNFO


# -- LOG ADAPTER -------------------------------------------------------------

class PlexLogAdapter(object):
    """
    Adapts Plex Log class to standard python logging style.

    This is a very simple remap of methods and does not provide
    full python standard logging functionality.
    """
    debug = Log.Debug
    info = Log.Info
    warn = Log.Warn
    error = Log.Error
    critical = Log.Critical
    exception = Log.Exception


class XBMCLogAdapter(PlexLogAdapter):
    """
    Plex Log adapter that only emits debug statements based on preferences.
    """
    @staticmethod
    def debug(*args, **kwargs):
        """
        Selective logging of debug message based on preference.
        """
        if preferences['debug']:
            Log.Debug(*args, **kwargs)

log = XBMCLogAdapter


# -- HELPER FUNCTIONS --------------------------------------------------------

VIDEO_FILE_BASE_REGEX = re.compile(
    r'(?is)\s*-\s*(cd|dvd|disc|disk|part|pt|d)\s*[0-9]$'
)


def get_base_file(video_file):
    """
    Get a Movie's base filename.

    This strips the video file extension and any CD / DVD or Part
    information from the video's filename.

    :param video_file: filename to be processed
    :return: string containing base file name
    """
    # split the filename and extension
    base, extension = os.path.splitext(video_file)
    del extension  # video file's extension is not used
    # Strip CD / DVD / Part information from file name
    base = VIDEO_FILE_BASE_REGEX.sub('', base)
    # Repeat a second time
    base = VIDEO_FILE_BASE_REGEX.sub('', base)
    return base


def get_related_file(video_file, file_extension):
    """
    Get a file related to the Video with a different extension.

    :param video_file: the filename of the associated video
    :param file_extension: the related files extension
    :return: a filename for a related file
    """
    return get_base_file(video_file) + file_extension


MOVIE_NAME_REGEX = re.compile(r' \(.*\)')


def get_movie_name_from_folder(folder_path, with_year):
    """
    Get the name of the movie from the folder.

    :param folder_path:
    :param with_year:
    :return:
    """
    # Split the folder into a list of paths
    folder_split = os.path.normpath(folder_path).split(os.sep)

    if folder_split[-1] == 'VIDEO_TS':  # If the folder is from a DVD
        # Strip the VIDEO_TS folder
        base = os.path.join(*folder_split[1:len(folder_split) - 1])
        name = folder_split[-2]
    else:
        base = os.path.join(*folder_split)
        name = folder_split[-1]

    if with_year:  # then apply the MOVIE_NAME_REGEX to strip year information
        name = MOVIE_NAME_REGEX.sub('', name)

    # Append the Movie name from folder to the end of the path
    movie_name = os.path.join(base, name)
    log.debug('Movie name from folder{with_year}: {name}'.format(
        with_year=' (with year)' if with_year else '',
        name=movie_name,
    ))
    return movie_name


def check_file_paths(file_names, file_type=None):
    """
    CHeck a list of file names and return the first one found.

    :param file_names: An iterable of file names to check
    :param file_type: (Optional) Type of file searched for. Used for logging.
    :return: a valid filename or None
    """
    for filename in file_names:
        log.debug('Trying {name}'.format(name=filename))
        if os.path.exists(filename):
            log.info('Found {type} file {name}'.format(
                type=file_type if file_type else 'a',
                name=filename,
            ))
            return filename
    else:
        log.info('No {type} file found! Aborting!'.format(
            type=file_type if file_type else 'valid'
        ))


def remove_empty_tags(document):
    """
    Removes empty XML tags.

    :param document: An HTML element object.
        see: http://lxml.de/api/lxml.etree._Element-class.html
    :return:
    """
    empty_tags = []
    for xml_tag in document.iter('*'):
        if not(len(xml_tag) or (xml_tag.text and xml_tag.text.strip())):
                empty_tags.append(xml_tag.tag)
                xml_tag.getparent().remove(xml_tag)
    log.debug('Empty XMLTags removed: {number} {tags}'.format(
        number=len(empty_tags) or None,
        tags=sorted(set(empty_tags)) or ''
    ))
    return document


UNESCAPE_REGEX = re.compile('&#?\w+;')


def unescape(markup):
    """
    Removes HTML or XML character references and entities from a text.
    Copyright:
        http://effbot.org/zone/re-sub.htm October 28, 2006 | Fredrik Lundh
    :param markup: The HTML (or XML) source text.
    :return: The plain text, as a Unicode string, if necessary.
    """

    def fix_up(match):
        """
        Convert a match from a character reference or named entity to unicode.

        :param match:  A regex match to attempt to convert to unicode
        :return: unescaped character or original text
        """
        element = match.group(0)
        if element.startswith('&#'):  # character reference
            start, base = (3, 16) if element.startswith('&#x') else (2, 10)
            try:
                return unichr(int(element[start:-1], base))
            except ValueError:
                pass
        else:  # named entity
            try:
                element = unichr(name2codepoint[element[1:-1]])
            except KeyError:
                pass
        return element  # leave as is

    return UNESCAPE_REGEX.sub(fix_up, markup)
