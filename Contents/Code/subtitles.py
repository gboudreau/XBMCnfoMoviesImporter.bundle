import os
import re
from __init__ import PlexLogAdapter
from __init__ import XBMCLogAdapter
from __init__ import preferences
from __init__ import log

def process_subtitle_files(part):
    """
    Search for related subtitle files and add them to the media item.  

    This function searches for subtitle files related to a given part in the part's folder
    It will also attempt to locate related files in a global subtitle folder
    These subtitles will be validated and added to the media item

    :param part: The part of the movie to use for searching
    :return: list containing related subtitle files
    """
    subtitle_files = []
    SUB_EXT = [ '.idx', '.sub', '.srt', '.smi', '.utf', '.utf8', '.utf-8', '.rt', '.ssa', '.ass', '.aqt', '.jss', '.txt', '.psb' ]
    (part_file_path, part_file_name) = os.path.split(part.file)
    (part_file_base_name, part_file_ext) = os.path.splitext(part_file_name)
    search_paths = [ part_file_path ]
    
    try:
        if preferences['subglobalpath'] == None:
            log.debug("No global subtitle folder has been set")
        elif os.path.isdir(preferences['subglobalpath']):
            search_paths.append(preferences['subglobalpath'])
        else:
            log.debug("The global subtitle folder '{}' does not exist".format(preferences['subglobalpath']))
    except Exception as e:
        log.debug("Unable to access global subtitle folder: '{}'".format(preferences['subglobalpath']))
        log.debug("Exception Message: {}".format(str(e)))
    
    for search_path in search_paths:
        log.debug("Searching for subtitles in: {}".format(search_path))
        sub_files_in_path = 0
        for file in os.listdir(search_path):
            # If we are dealing with a folder, skip
            if not os.path.isfile(os.path.join(search_path, file)):
                continue
            
            # Extract the basename and file extension from the file
            (file_base_name, file_ext) = os.path.splitext(file)
            file_ext = file_ext.lower()
            
            # If the file does not have a valid extension or does not match the part file name, skip it
            if not ( file_ext in SUB_EXT and file_base_name.startswith(part_file_base_name) ):
                continue
            
            # Set/Reset some default variable values for every file
            sub_flag = ""
            lang_code = "xx" # Default to the 'unknown' language code
            forced = ''
            default = ''
            sub_codec = None
            sub_format = None
            full_name = os.path.join(search_path, file)
            full_name_no_ext = os.path.join(search_path, file_base_name)
            
            sub_files_in_path += 1
            log.debug("    Found subtitle file: {}".format(file))

            # Remove the video file part from the subtitle file
            file_name_sufix = (file_base_name[len(part_file_base_name):]).lower()

            # Extract the parts separated by a spac`e ( ), period (.) or dash (-)
            # These could represent a language code, language name, or subtitle flag (Forced|Normal|Default)
            suffix_parts = re.split(r"\s|\.|-", file_name_sufix)[1:]

            # Make sure there are only one or two parts, otherwise ignore the suffix
            if len(suffix_parts) == 1 or len(suffix_parts) == 2:
                for suffix_part in suffix_parts:
                    # Set the subtitle type flag otherwise search for the language code
                    if suffix_part == 'forced':
                        forced = '1'
                    elif suffix_part == 'default':
                        default = '1'
                    elif suffix_part == 'normal':
                        pass
                    else:
                        lang_code = Locale.Language.Match(suffix_part)

            # Track some vars for debugging and cleaning up
            file_vars = {
                "full_name": full_name,
                "name": file,
                "base_name": file_base_name,
                "ext": file_ext,
                "lang_code": lang_code,
                "forced": forced,
                "default": default,
                "full_name_no_ext": full_name_no_ext,
                "format": "",
                "codec": "",
                "status": ""
            }
            
            idx_full_name = full_name_no_ext + '.idx'
            if file_ext == '.sub' and os.path.exists(idx_full_name):
                
                # Process vobsub formatted files
                log.debug("Attempting to process subtitle file: {} for found .sub file: []}".format(idx_full_name, full_name))
                idx_content = Core.storage.load(idx_full_name)
                
                if idx_content.count('VobSub index file') == 0:
                    log.debug("Unknown format, ignoring idx subtitle file: {}".format(idx_full_name))
                    file_vars["status"] = "error"
                    subtitle_files.append(file_vars)
                    continue
                
                idx_language_index = 0
                idx_languages = re.findall('\nid: ([A-Za-z]{2})', idx_content)
                
                # If no languages are found, move on to the next file
                if idx_language_index < 1:
                    log.debug("Unable to find languages in file: {}".format(idx_full_name))
                    file_vars["status"] = "error"
                    subtitle_files.append(file_vars)
                    continue
                    
                for idx_lang_code in idx_languages:
                    log.debug("Found landuage '{}' in file: {}".format(idx_lang_code, idx_full_name))
                    part.subtitles[idx_lang_code][file_base_name] = Proxy.LocalFile(idx_full_name, index = str(idx_language_index), format = "vobsub")
                    idx_language_index += 1
                    
                    file_vars["lang_code"] = idx_lang_code
                    file_vars["format"] = "vobsub"
                    file_vars["status"] = "success"
                    subtitle_files.append(file_vars)
                
                # When finished processing all the languages in the idx file, move on to the next file  
                continue
                
            elif file_ext in ['.txt', '.sub']:
                try:
                    #sub_file_contents = Core.storage.load(full_name)
                    sub_file_lines = [ line.strip() for line in Core.storage.load(full_name).splitlines(True) ]
                    if '[SUBTITLE]' in lines[1]:
                        sub_format = 'subviewer'
                    elif re.match('^\{[0-9]+\}\{[0-9]*\}', lines[1]):
                        sub_format = 'microdvd'
                    elif re.match('^[0-9]{1,2}:[0-9]{2}:[0-9]{2}[:=,]', lines[1]):
                        sub_format = 'txt'
                    else:
                        log.debug("Unknown format, ignoring subtitle file: {}".format(full_name))
                        subtitle_files.append(file_vars)
                        continue
                except Exception as err:
                    log.debug("An error occurred while processing subtitle file: {}".format(full_name))
                    log.debug("Details: {}".format(err))
                    subtitle_files.append(file_vars)
                    continue
                
            elif file_ext in ['.ass', '.ssa', '.smi', '.srt', '.psb']:
                sub_codec = file_ext[1:].replace('ass', 'ssa')
            
            if sub_format is None:
                sub_format = sub_codec
            
            part.subtitles[lang_code][file_base_name] = Proxy.LocalFile(full_name, codec = sub_codec, format = sub_format, default = default, forced = forced)
            
            file_vars["status"] = "success"
            file_vars["format"] = sub_format
            file_vars["codec"] = sub_codec
            subtitle_files.append(file_vars)
        
        if sub_files_in_path < 1:
            log.debug("    No subtitle files found")
        
    return subtitle_files
    
def cleanup_subtitle_entries(part, subtitle_files):
    
    # Create a dictionary to map the file basenames to the language codes
    dict_code_basename = {}
    
    # Loop through the list of found files and add the mappings to the dictionary
    for subtitle_file in subtitle_files:
        
        # Skip files without valid subtitles
        if subtitle_file["status"] != "success":
            continue
        
        # Make sure the language key eists in the dictionary as a list
        if not dict_code_basename.has_key(subtitle_file["lang_code"]):
            dict_code_basename[subtitle_file["lang_code"]] = []
        
        # Add the basename to the list for the appropriate language code
        dict_code_basename[subtitle_file["lang_code"]].append(subtitle_file["base_name"])
        
    # Remove the subtitles files that are not valid
    for lang_code in dict_code_basename.keys():
        part.subtitles[lang_code].validate_keys(dict_code_basename[lang_code])
    
    # Remove the languages that are not valid
    for lang_code in list(set(part.subtitles.keys()) - set(dict_code_basename.keys())):
        part.subtitles[lang_code].validate_keys({})
