XBMCnfoMoviesImporter.bundle-for-Plex
=====================================
Installation:
It is recommended to install the [WebTools plugin](http://forums.plex.tv/discussion/126254/rel-webtools-2-x).

Using the Unsupported Appstore from WebTools it is possible
to easily install, update and remove the Agent, without having
to go through the hassle of manually downloading, unzipping,
renaming and moving it to the correct directory each time.

After successfully installing WebTools please login and select the
"Unsupported Appstore" Module. There you click on the "Agent" tab,
scroll down and can now easily install the XBMCnfoMoviesImporter.

Manual Installation:
Not recommended, but possible if you know what you are doing.

Download the [zipped bundle](https://github.com/gboudreau/XBMCnfoMoviesImporter.bundle/archive/master.zip) from github,
extract it,
rename it to **XBMCnfoMoviesImporter.bundle**,
find the [Plex Media Server data directory](https://support.plex.tv/hc/en-us/articles/202915258-Where-is-the-Plex-Media-Server-data-directory-located-)
move the .bundle folder to the Plug-ins directory,
restart plex and test,
if necessary change the owner and permissions of the .bundle and
restart plex again.

User MattJ from the plex forum reported the following steps to install on ubuntu 14.04:
- Download from github and unzip
- Remove "-master" from the end of both folder names.
- Copy them to the folder:  /var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-ins
- Find the group number for user "plex" by command "id plex".
- "cd" to folder in step 3 and change ownership of both XBMC bundles: "sudo chown plex:{gid} XBMC*"
- run "sudo service plexmediaserver restart".
Done.
